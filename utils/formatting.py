def usd(value):
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "0.0%"


def risk_label(score):
    try:
        score = int(score)
    except Exception:
        score = 0
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"
