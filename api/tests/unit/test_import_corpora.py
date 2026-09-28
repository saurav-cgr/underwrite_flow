"""Bootstrap import coverage for mounted synthetic guideline corpora."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from underwriteflow.knowledge import import_corpora as import_module
from underwriteflow.config import Settings


# Verify every mounted corpus is imported as a draft without activation.
def test_bootstrap_imports_every_corpus_as_draft(monkeypatch) -> None:
    session = AsyncMock()
    session.scalar.return_value = SimpleNamespace(id=uuid4())
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)
    database = MagicMock()
    database.session_factory.return_value = session_context
    database.close = AsyncMock()
    service = MagicMock()
    service.import_guideline = AsyncMock(
        side_effect=lambda *args, **kwargs: SimpleNamespace(status="draft")
    )

    settings = Settings(generation_provider="fake")
    provider = object()
    monkeypatch.setattr(
        import_module, "get_settings", MagicMock(return_value=settings)
    )
    monkeypatch.setattr(
        import_module,
        "build_embedding_provider",
        MagicMock(return_value=provider),
    )
    monkeypatch.setattr(
        import_module, "Database", MagicMock(return_value=database)
    )
    monkeypatch.setattr(
        import_module, "KnowledgeService", MagicMock(return_value=service)
    )

    root = Path("knowledge-config")
    import_module.asyncio.run(import_module.import_corpora(root))

    paths = sorted(root.glob("*/*.yaml"))
    assert service.import_guideline.await_count == len(paths)
    imported_text = [
        call.args[1]
        for call in service.import_guideline.await_args_list
    ]
    assert imported_text == [path.read_text() for path in paths]
    assert all(
        call.args[2] is not None
        for call in service.import_guideline.await_args_list
    )
    assert import_module.build_embedding_provider.call_args.args == (
        settings,
    )
    assert import_module.KnowledgeService.call_args.kwargs == {
        "embedding_provider": provider
    }
    service.activate.assert_not_called()
