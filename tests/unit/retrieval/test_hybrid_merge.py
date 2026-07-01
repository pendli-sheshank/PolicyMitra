from uuid import uuid4

from retrieval.hybrid import reciprocal_rank_fusion


def test_chunk_ranked_first_in_both_lists_wins():
    a, b, c = uuid4(), uuid4(), uuid4()
    bm25_ranked = [(a, 0.9), (b, 0.5), (c, 0.1)]
    dense_ranked = [(a, 0.8), (c, 0.6), (b, 0.2)]

    fused = reciprocal_rank_fusion([bm25_ranked, dense_ranked])

    assert fused[a] > fused[b]
    assert fused[a] > fused[c]


def test_chunk_present_in_only_one_list_still_scores():
    a, b = uuid4(), uuid4()
    bm25_ranked = [(a, 0.9)]
    dense_ranked = [(b, 0.9)]

    fused = reciprocal_rank_fusion([bm25_ranked, dense_ranked])

    assert a in fused
    assert b in fused


def test_appearing_in_both_lists_beats_appearing_in_one():
    a, b = uuid4(), uuid4()
    bm25_ranked = [(a, 0.9), (b, 0.1)]
    dense_ranked = [(a, 0.9)]

    fused = reciprocal_rank_fusion([bm25_ranked, dense_ranked])

    assert fused[a] > fused[b]
