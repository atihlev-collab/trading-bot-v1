# ==========================================
# Trading Bot V3
# Ranking Engine
# ==========================================


def rank_signals(signals):

    if not signals:
        return []

    ranked = []

    for signal in signals:

        score = 0

        # Confidence (0-40)
        score += signal["confidence"] * 0.40

        # Strategy score (0-30)
        score += signal["score"] * 2

        # Trend (0-10)
        score += min(
            signal["trend_strength"] * 10,
            10,
        )

        # Momentum (0-10)
        score += min(
            signal["momentum"] * 1000,
            10,
        )

        # Volume (0-10)
        if signal["volume_ma"] > 0:

            volume_ratio = (
                signal["volume"] /
                signal["volume_ma"]
            )

            score += min(
                volume_ratio * 5,
                10,
            )

        signal["rank"] = round(score, 2)

        ranked.append(signal)

    ranked.sort(
        key=lambda x: x["rank"],
        reverse=True,
    )

    return ranked


# ==========================================
# Best Signal
# ==========================================

def best_signal(signals):

    ranked = rank_signals(signals)

    if not ranked:
        return None

    return ranked[0]


# ==========================================
# Top Signals
# ==========================================

def top_signals(
    signals,
    limit=3,
):

    ranked = rank_signals(signals)

    return ranked[:limit]