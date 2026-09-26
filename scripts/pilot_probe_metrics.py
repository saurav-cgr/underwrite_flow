"""Measurement helpers for the bounded synthetic pilot probe."""

import asyncio
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from threading import Event, Lock
from time import perf_counter, sleep
from uuid import UUID

import psycopg
from PIL import Image, ImageDraw

from underwriteflow.providers.extraction import LocalDocumentExtractor
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.providers.schemas import ExtractionRequest, ExtractionResult

OCR_SAMPLES = 3
CASE_TABLES = (
    "cases",
    "submissions",
    "documents",
    "extracted_fields",
    "validations",
    "risk_signals",
    "recommendations",
    "reviews",
    "audit_events",
    "handoffs",
)


@dataclass(frozen=True)
class CohortRun:
    """Measurements collected for one bounded concurrent cohort."""

    size: int
    elapsed_seconds: float
    ordinary_p95_ms: float
    review_ready_p95_ms: float
    provider_p95_ms: float
    provider_max_active: int
    provider_calls_per_case: int
    database_max_checked_out: int
    database_pool_size: int
    stored_bytes_per_case: float
    upload_bytes_per_case: float
    checkpoint_bytes_per_case: float
    queue_p95_ms: float


class MeasuredFakeProvider:
    """Expose latency and active-call counts around the deterministic fake."""

    name = "fake"

    # Initialize thread-safe counters around one stateless fake provider.
    def __init__(self) -> None:
        self.delegate = FakeProvider()
        self.lock = Lock()
        self.durations_ms: list[float] = []
        self.active = 0
        self.max_active = 0

    # Clear counters between cohorts when no call is active.
    def reset(self) -> None:
        with self.lock:
            assert self.active == 0
            self.durations_ms.clear()
            self.max_active = 0

    # Return an immutable view of the current measurements.
    def snapshot(self) -> tuple[list[float], int]:
        with self.lock:
            return list(self.durations_ms), self.max_active

    # Measure one fake extraction while exposing real scheduled overlap.
    async def extract(
        self, request: ExtractionRequest
    ) -> ExtractionResult:
        started = perf_counter()
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0)
            return await self.delegate.extract(request)
        finally:
            elapsed = (perf_counter() - started) * 1000
            with self.lock:
                self.active -= 1
                self.durations_ms.append(elapsed)


# Calculate a nearest-rank percentile for a non-empty bounded sample.
def percentile(values: list[float], percent: int) -> float:
    ordered = sorted(values)
    rank = max(1, ceil(len(ordered) * percent / 100))
    return ordered[rank - 1]


# Sample checked-out database connections until the cohort finishes.
def sample_pool(stop: Event, pool, samples: list[int]) -> None:
    while not stop.is_set():
        samples.append(pool.checkedout())
        sleep(0.002)


# Sum PostgreSQL row storage for fixed case-owned tables and checkpoints.
def storage_metrics(
    database_url: str, case_ids: list[UUID]
) -> tuple[float, float, float]:
    sync_url = database_url.replace("postgresql+asyncpg", "postgresql")
    thread_ids = [f"case-{case_id}:cycle-0" for case_id in case_ids]
    stored = 0
    checkpoint = 0
    with psycopg.connect(sync_url) as connection:
        with connection.cursor() as cursor:
            for table in CASE_TABLES:
                column = "id" if table == "cases" else "case_id"
                cursor.execute(
                    f"SELECT COALESCE(sum(pg_column_size(t)), 0) "
                    f"FROM {table} t WHERE {column} = ANY(%s)",
                    (case_ids,),
                )
                stored += int(cursor.fetchone()[0])
            cursor.execute(
                "SELECT COALESCE(sum(byte_size), 0) FROM documents "
                "WHERE case_id = ANY(%s)",
                (case_ids,),
            )
            uploads = int(cursor.fetchone()[0])
            for table in (
                "checkpoints",
                "checkpoint_blobs",
                "checkpoint_writes",
            ):
                cursor.execute(
                    f"SELECT COALESCE(sum(pg_column_size(t)), 0) "
                    f"FROM {table} t WHERE thread_id = ANY(%s)",
                    (thread_ids,),
                )
                checkpoint += int(cursor.fetchone()[0])
    count = len(case_ids)
    return (
        (stored + checkpoint) / count,
        uploads / count,
        checkpoint / count,
    )


# Measure local OCR seconds per page on a fictional one-page image.
def measure_ocr_seconds_per_page() -> float:
    durations: list[float] = []
    with TemporaryDirectory() as directory:
        path = Path(directory) / "synthetic-ocr.png"
        image = Image.new("RGB", (1200, 300), "white")
        ImageDraw.Draw(image).text(
            (40, 80),
            "SYNTHETIC DEMONSTRATION RECORD 001",
            fill="black",
        )
        image.save(path)
        extractor = LocalDocumentExtractor()
        for _ in range(OCR_SAMPLES):
            started = perf_counter()
            result = extractor.extract(path, "image/png")
            durations.append(perf_counter() - started)
            assert result.method == "ocr"
            assert len(result.pages) == 1
    return median(durations)
