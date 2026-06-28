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
