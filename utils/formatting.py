def usd(value: float) -> str:
    return f"${float(value):,.2f}"


def pct(value: float) -> str:
    return f"{float(value):.1f}%"
