from underwriteflow.knowledge.retrieval import fuse_ranks


# Verify reciprocal rank fusion uses k=60 and stable passage-key ties.
def test_fuse_ranks_uses_rrf_and_stable_ties() -> None:
    results = fuse_ranks(
        ["passage-b", "passage-a"],
        ["passage-a", "passage-b"],
    )

    assert [item["passage_key"] for item in results] == [
        "passage-a",
        "passage-b",
    ]
    assert results[0]["score"] == 1 / 61 + 1 / 62
