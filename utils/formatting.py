def usd(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    return f"${value:,.2f}"


def pct(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    return f"{value:.1f}%"


def num(value, decimals=2):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    return round(value, decimals)
