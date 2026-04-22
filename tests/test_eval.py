from src.agents.eval import score_report


def test_score_report_metrics_and_pass_gate():
    report = """
## Executive Summary
Quantum attacks are discussed [source](https://a.com).

## Key Findings
Shor breaks RSA [paper](https://b.com) and migration is needed.

## Open Questions
Timeline uncertainty remains.
""".strip()

    findings = [
        {"summary": "finding one", "confidence": 2},
        {"summary": "finding two", "confidence": 4},
        {"summary": "finding three", "confidence": 5},
    ]

    result = score_report(report, findings)

    assert result["citation_ratio"] == 0.67
    assert result["total_citations"] == 2
    assert result["unique_sources"] == 2
    assert result["word_count"] > 0
    assert result["questions_covered"] == 3
    assert result["low_confidence_filtered"] == 1
    assert result["passed"] is True


def test_score_report_empty_report_fails_gate():
    result = score_report("", [{"summary": "x", "confidence": 1}])

    assert result["citation_ratio"] == 0.0
    assert result["total_citations"] == 0
    assert result["unique_sources"] == 0
    assert result["passed"] is False
