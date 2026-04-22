from src.agents.critic import _parse_scores


def test_parse_scores_reads_numbered_values():
    text = """
CONFIDENCE_SCORES:
1: 5
2: 3
3: 1
VERDICT: APPROVED
""".strip()

    assert _parse_scores(text, 3) == [5, 3, 1]


def test_parse_scores_defaults_missing_entries_to_two():
    text = """
CONFIDENCE_SCORES:
1: 4
VERDICT: NEEDS_WORK: more sources needed
""".strip()

    assert _parse_scores(text, 3) == [4, 2, 2]


def test_parse_scores_ignores_out_of_range_indices():
    text = """
CONFIDENCE_SCORES:
1: 5
4: 1
VERDICT: APPROVED
""".strip()

    assert _parse_scores(text, 3) == [5, 2, 2]
