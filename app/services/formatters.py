"""Currency and number formatting utilities for Indian locale."""


def format_inr(amount: float, short: bool = True) -> str:
    """
    Format an amount in Indian Rupee notation.
    If short=True: use L (lakhs) / Cr (crores) suffixes for readability.
    """
    if amount is None:
        return "₹0"

    negative = amount < 0
    abs_amount = abs(amount)

    if short:
        if abs_amount >= 1e7:
            formatted = f"₹{abs_amount / 1e7:.2f} Cr"
        elif abs_amount >= 1e5:
            formatted = f"₹{abs_amount / 1e5:.2f} L"
        elif abs_amount >= 1e3:
            formatted = f"₹{abs_amount / 1e3:.1f} K"
        else:
            formatted = f"₹{abs_amount:,.0f}"
    else:
        formatted = "₹" + _indian_comma(abs_amount)

    return ("-" + formatted) if negative else formatted


def _indian_comma(amount: float) -> str:
    """Apply Indian comma grouping: last 3 digits, then groups of 2."""
    integer_part = int(amount)
    decimal_part = round(amount - integer_part, 2)

    s = str(integer_part)
    if len(s) <= 3:
        result = s
    else:
        result = s[-3:]
        s = s[:-3]
        while s:
            result = s[-2:] + "," + result
            s = s[:-2]

    if decimal_part > 0:
        result += f".{int(round(decimal_part * 100)):02d}"
    return result


def format_usd(amount_inr: float, usd_rate: float) -> str:
    """Format INR amount as USD equivalent."""
    if usd_rate <= 0:
        return ""
    usd = amount_inr / usd_rate
    if abs(usd) >= 1e6:
        return f"~${usd / 1e6:.2f}M"
    elif abs(usd) >= 1e3:
        return f"~${usd / 1e3:.1f}K"
    return f"~${usd:,.0f}"


def format_percent(value: float, total: float) -> str:
    """Return percentage string, e.g. '12.34%'."""
    if total == 0:
        return "0.00%"
    return f"{value / total * 100:.2f}%"


def format_gain(current: float, cost: float) -> str:
    """Return gain/loss string with sign and percent."""
    gain = current - cost
    pct = (gain / cost * 100) if cost != 0 else 0
    sign = "+" if gain >= 0 else ""
    return f"{sign}{format_inr(gain, short=True)} ({sign}{pct:.1f}%)"


def format_date(date_str: str) -> str:
    """Convert YYYY-MM-DD to DD-MMM-YYYY for display."""
    if not date_str or len(date_str) < 10:
        return date_str or ""
    try:
        from datetime import date
        d = date.fromisoformat(date_str[:10])
        return d.strftime("%d-%b-%Y")
    except Exception:
        return date_str


def format_rate(rate: float) -> str:
    return f"{rate:.2f}%" if rate is not None else ""
