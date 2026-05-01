"""
STEP 5 — Observability: rubric-based evaluation + run metrics
=============================================================
Replaces the thin eval.py with a proper rubric scorer that measures:

  coverage        — did the report address every planned question?
  citation_density — URLs per 500 words (grounded = better)
  coherence        — paragraph count, average sentence length
  word_count       — raw length signal
  critic_calibration — did the critic's confidence track the final score?

HOW TO USE
----------
    from agents.eval import score_report, score_findings, calibration_check

    # After the writer produces the report:
    scores = score_report(state["report"], state["plan"])

    # After the researcher produces findings (partial eval per loop):
    finding_scores = score_findings(state["findings"], state["plan"])

    # Check whether the critic was well-calibrated:
    cal = calibration_check(critic_confidence=4, report_score=0.35)
    print(cal)  # {"calibrated": False, "gap": 0.65, "note": "..."}

SAVING TO RUN
-------------
    result["eval_scores"] = score_report(result["report"], result["plan"])
    run_id = save_run(topic, result)
"""

from __future__ import annotations

import re
from typing import Any


# ── Regex helpers ──────────────────────────────────────────────────────────────

CITATION_PATTERN = re.compile(r"https?://\S+")
SENTENCE_SPLIT = re.compile(r"[.!?]+\s+")


# ── Report-level scoring ──────────────────────────────────────────────────────

def score_report(report: str, plan: list[str]) -> dict[str, Any]:
    """
    Score a completed report against the research plan.

    Returns a dict suitable for storage in the run JSON:
    {
        "word_count": int,
        "questions_covered": int,
        "questions_total": int,
        "coverage_pct": float,          # 0.0 – 1.0
        "citation_count": int,
        "citation_density": float,      # citations per 500 words
        "avg_sentence_length": float,   # words per sentence
        "paragraph_count": int,
        "overall": float,               # 0.0 – 1.0 composite score
    }
    """
    if not report:
        return _empty_scores(plan)

    words = report.split()
    word_count = len(words)

    citations = _real_citations(report)
    citation_count = len(set(citations))
    citation_density = (citation_count / max(1, word_count)) * 500

    sentences = [s for s in SENTENCE_SPLIT.split(report) if s.strip()]
    avg_sentence_length = word_count / max(1, len(sentences))

    paragraphs = [p for p in report.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs)

    # Coverage: count how many plan questions have a relevant paragraph
    covered = sum(
        1
        for q in plan
        if _question_covered(q, report)
    )
    questions_total = len(plan)
    coverage_pct = covered / max(1, questions_total)

    # Composite score (weights are intentionally interpretable)
    # coverage is most important (0.5), citations next (0.3), length sanity (0.2)
    length_score = min(1.0, word_count / 400)  # 400+ words = full score
    citation_score = min(1.0, citation_density / 3)  # 3 citations/500w = full
    overall = round(
        0.50 * coverage_pct
        + 0.30 * citation_score
        + 0.20 * length_score,
        3,
    )

    return {
        "word_count": word_count,
        "questions_covered": covered,
        "questions_total": questions_total,
        "coverage_pct": round(coverage_pct, 3),
        "citation_count": citation_count,
        "citation_density": round(citation_density, 2),
        "avg_sentence_length": round(avg_sentence_length, 1),
        "paragraph_count": paragraph_count,
        "overall": overall,
    }


def score_findings(findings: list[str], plan: list[str]) -> dict[str, Any]:
    """
    Lighter eval on raw findings (before the writer runs).
    Useful for the Critic to decide whether to approve.
    """
    if not findings:
        return {"findings_count": 0, "coverage_pct": 0.0, "has_sources": False}

    combined = " ".join(findings)
    citations = _real_citations(combined)
    covered = sum(1 for q in plan if _question_covered(q, combined))

    return {
        "findings_count": len(findings),
        "coverage_pct": round(covered / max(1, len(plan)), 3),
        "has_sources": len(citations) > 0,
        "source_count": len(set(citations)),
    }


def _real_citations(text: str) -> list[str]:
    """Extract citation-like URLs but exclude obvious search-result URLs.

    Filters out DuckDuckGo and Google search result links which are not
    actual page citations.
    """
    urls = CITATION_PATTERN.findall(text or "")
    filtered = [u for u in urls if "duckduckgo.com/search" not in u and "google.com/search" not in u]
    return filtered


# ── Critic calibration ────────────────────────────────────────────────────────

def calibration_check(
    critic_confidence: int,
    report_overall: float,
) -> dict[str, Any]:
    """
    Compare the Critic's self-assessed confidence (1–5) against the
    final report's overall score (0.0–1.0).

    A well-calibrated critic scores 5/5 when the report scores 0.8+,
    and 1/5 when it scores below 0.2.

    Returns {"calibrated": bool, "gap": float, "note": str}
    """
    # Normalise confidence to 0–1
    expected_score = (critic_confidence - 1) / 4.0
    gap = round(abs(expected_score - report_overall), 3)
    calibrated = gap <= 0.25  # within 25% → acceptable

    if gap <= 0.1:
        note = "Well calibrated"
    elif expected_score > report_overall:
        note = f"Critic overconfident by {gap:.0%}"
    else:
        note = f"Critic underconfident by {gap:.0%}"

    return {"calibrated": calibrated, "gap": gap, "note": note}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _question_covered(question: str, text: str) -> bool:
    """
    Heuristic: extract the 3 most significant words from the question and
    check whether all three appear in the text (case-insensitive).
    This is intentionally simple — good enough for portfolio eval.
    """
    stopwords = {
        "what", "how", "why", "when", "where", "who", "which", "is", "are",
        "does", "do", "the", "a", "an", "in", "of", "to", "for", "and",
        "have", "has", "been", "key", "main", "major",
    }
    words = re.findall(r"\b[a-z]{4,}\b", question.lower())
    keywords = [w for w in words if w not in stopwords][:3]
    if not keywords:
        return False
    text_lower = text.lower()
    return all(kw in text_lower for kw in keywords)


def _empty_scores(plan: list[str]) -> dict[str, Any]:
    return {
        "word_count": 0,
        "questions_covered": 0,
        "questions_total": len(plan),
        "coverage_pct": 0.0,
        "citation_count": 0,
        "citation_density": 0.0,
        "avg_sentence_length": 0.0,
        "paragraph_count": 0,
        "overall": 0.0,
    }
