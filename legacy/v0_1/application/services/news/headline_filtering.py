from typing import Any

"""
Deterministic headline filtering layer.

Purpose:
- remove noise before intelligence scoring
- filter irrelevant or low-signal financial content
- normalize headline quality for downstream systems

This is a FAST GATE, not an intelligence layer.
"""

# ============================================================
# FILTER CONFIGS
# ============================================================

NOISE_KEYWORDS = {
    "celebrity",
    "entertainment",
    "sports",
    "football",
    "nba",
    "nfl",
    "movie",
    "music",
    "fashion",
    "gossip",
}

LOW_SIGNAL_KEYWORDS = {
    "opinion",
    "commentary",
    "op-ed",
    "analysis:",
    "review",
    "sponsored",
    "advertisement",
}

HIGH_SIGNAL_KEYWORDS = {
    "fed",
    "inflation",
    "cpi",
    "ppi",
    "interest rate",
    "rates",
    "yield",
    "liquidity",
    "recession",
    "gdp",
    "earnings",
    "jobs",
    "unemployment",
    "market",
    "stock",
    "spy",
    "s&p",
}

# ============================================================
# MAIN ENTRYPOINT
# ============================================================


def filter(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Filter and score headlines deterministically.
    """

    filtered = []

    for article in articles:
        headline = _get_text(article)

        if not headline:
            continue

        score = _score_headline(headline)

        if score < 0.3:
            continue

        article["headline_score"] = score

        filtered.append(article)

    return filtered


# ============================================================
# SCORING ENGINE
# ============================================================


def _score_headline(
    text: str,
) -> float:

    text_lower = text.lower()

    score = 0.5  # base neutrality

    # ========================================================
    # NOISE PENALTY
    # ========================================================

    if any(kw in text_lower for kw in NOISE_KEYWORDS):
        score -= 0.6

    # ========================================================
    # LOW SIGNAL PENALTY
    # ========================================================

    if any(kw in text_lower for kw in LOW_SIGNAL_KEYWORDS):
        score -= 0.2

    # ========================================================
    # HIGH SIGNAL BOOST
    # ========================================================

    if any(kw in text_lower for kw in HIGH_SIGNAL_KEYWORDS):
        score += 0.4

    # ========================================================
    # FINANCIAL KEYWORD DENSITY BONUS
    # ========================================================

    finance_hits = sum(1 for kw in HIGH_SIGNAL_KEYWORDS if kw in text_lower)

    score += min(finance_hits * 0.05, 0.2)

    # ========================================================
    # LENGTH HEURISTIC (VERY SHORT HEADLINES ARE NOISY)
    # ========================================================

    if len(text) < 30:
        score -= 0.1

    # ========================================================
    # CLAMP
    # ========================================================

    return max(0.0, min(score, 1.0))


# ============================================================
# TEXT EXTRACTION
# ============================================================


def _get_text(
    article: dict[str, Any],
) -> str:

    return article.get("title") or article.get("headline") or ""
