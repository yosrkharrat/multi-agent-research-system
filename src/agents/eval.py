"""Lightweight report evaluation helpers."""

from __future__ import annotations

import re

CITATION_PATTERN = re.compile(r"\[.+?\]\(https?://[^\s)]+\)")


def score_report(report: str, findings: list[dict[str, object]]) -> dict[str, object]:
    """Validate report quality with citation-focused metrics."""

    paragraphs = [
        p for p in report.split("\n")
        if p.strip() and not p.lstrip().startswith("#")
    ]
    cited = sum(1 for p in paragraphs if CITATION_PATTERN.search(p))
    citation_ratio = (cited / len(paragraphs)) if paragraphs else 0.0
    citations = CITATION_PATTERN.findall(report)

    return {
        "citation_ratio": round(citation_ratio, 2),
        "total_citations": len(citations),
        "unique_sources": len(set(citations)),
        "word_count": len(report.split()),
        "questions_covered": sum(
            1
            for finding in findings
            if isinstance(finding, dict)
            and str(finding.get("summary", finding.get("content", ""))).strip()
        ),
        "low_confidence_filtered": sum(
            1
            for finding in findings
            if isinstance(finding, dict)
            and int(finding.get("confidence", 0)) < 3
        ),
        "passed": citation_ratio >= 0.6,
    }
