"""Deterministic specialist brief assembly."""

from underwriteflow.knowledge.brief import build_brief


EVIDENCE = [
    {
        "document_id": "doc-1",
        "filename": "identity_record.pdf",
        "source_locator": "storage/doc-1",
    },
    {
        "document_id": "doc-1",
        "field_name": "occupation_type",
        "value": "hazardous",
        "source_locator": "page:1",
    },
    {
        "field_name": "unlocated",
        "value": "ignored",
        "source_locator": None,
    },
]
VALIDATIONS = [
    {
        "rule_code": "hazardous_occupation_specialist",
        "status": "triggered",
        "route": "specialist",
    },
    {
        "rule_code": "high_cover_standard",
        "status": "clear",
        "route": "standard",
    },
]
PASSAGES = [
    {
        "title": f"Synthetic passage {index}",
        "body": "Synthetic guidance only.",
        "citation": {
            "version": "g1",
            "passage_key": f"passage-{index}",
        },
    }
    for index in range(4)
]


# Given specialist evidence, build a sourced brief with bounded suggestions.
def test_specialist_brief_lists_sources_rules_and_passages() -> None:
    brief = build_brief("specialist", EVIDENCE, VALIDATIONS, PASSAGES)

    assert brief is not None
    assert brief["evidence"] == [
        {
            "field_name": "occupation_type",
            "value": "hazardous",
            "document": "identity_record.pdf",
            "source_locator": "page:1",
        }
    ]
    assert brief["rules"] == ["hazardous_occupation_specialist"]
    assert brief["passages"] == PASSAGES
    assert brief["suggested_citations"] == [
        passage["citation"] for passage in PASSAGES[:3]
    ]


# Given a non-specialist route, do not produce any specialist brief.
def test_non_specialist_route_has_no_brief() -> None:
    assert build_brief("standard", EVIDENCE, VALIDATIONS, PASSAGES) is None


# Given no matched passage, preserve deterministic evidence and rules only.
def test_specialist_brief_allows_no_passages() -> None:
    brief = build_brief("specialist", EVIDENCE, VALIDATIONS, [])

    assert brief is not None
    assert brief["passages"] == []
    assert brief["suggested_citations"] == []
