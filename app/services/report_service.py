"""Data preparation for charts and tabular reports."""

from app.models import networth as nw_model


def get_chart_data(months: int = 0) -> dict:
    """
    Prepare chart-ready data from snapshot history.
    months=0 → all time; 12/36/60 → last N months.
    """
    snapshots = nw_model.get_snapshots_for_chart(months)
    if not snapshots:
        return {"dates": [], "gross": [], "net_worth": [], "liabilities": [],
                "debt": [], "equity": [], "gold": [], "real_estate": []}

    return {
        "dates": [s["snapshot_date"] for s in snapshots],
        "gross": [s["gross_assets"] for s in snapshots],
        "net_worth": [s["net_worth"] for s in snapshots],
        "liabilities": [s["total_liabilities"] for s in snapshots],
        "debt": [s["total_debt_assets"] for s in snapshots],
        "equity": [s["total_equity_assets"] for s in snapshots],
        "gold": [s["total_gold_assets"] for s in snapshots],
        "real_estate": [s["total_real_estate"] for s in snapshots],
        "pf": [s["total_pf"] for s in snapshots],
        "fd": [s["total_fd"] for s in snapshots],
        "bonds": [s["total_bonds"] for s in snapshots],
        "debt_mf": [s["total_debt_mf"] for s in snapshots],
        "equity_mf": [s["total_equity_mf"] for s in snapshots],
        "stocks": [s["total_stocks"] for s in snapshots],
        "gold_mf": [s["total_gold_mf"] for s in snapshots],
        "sgb": [s["total_sgb"] for s in snapshots],
    }


def get_tabular_report(period: str = "monthly") -> list[dict]:
    """
    Build a tabular report grouped by month/quarter/year.
    period: 'monthly' | 'quarterly' | 'yearly'
    """
    snapshots = nw_model.get_all_snapshots()
    if not snapshots:
        return []

    groups: dict[str, list] = {}
    for s in snapshots:
        d = s["snapshot_date"]
        if period == "monthly":
            key = d[:7]  # YYYY-MM
        elif period == "quarterly":
            month = int(d[5:7])
            quarter = (month - 1) // 3 + 1
            key = f"{d[:4]}-Q{quarter}"
        else:  # yearly
            key = d[:4]

        groups.setdefault(key, []).append(s)

    result = []
    for period_key in sorted(groups.keys()):
        # Use the last snapshot in each period
        s = groups[period_key][-1]
        result.append({
            "period": period_key,
            "gross_assets": s["gross_assets"],
            "total_liabilities": s["total_liabilities"],
            "net_worth": s["net_worth"],
            "debt_assets": s["total_debt_assets"],
            "equity_assets": s["total_equity_assets"],
            "gold_assets": s["total_gold_assets"],
            "real_estate": s["total_real_estate"],
            "snapshot_date": s["snapshot_date"],
        })
    return result
