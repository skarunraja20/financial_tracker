"""Debt Mutual Funds widget."""

from app.models import mutual_fund as mf_model
from app.ui.mf_base_widget import MFBaseWidget
from app.core.constants import FUND_CATEGORY_DEBT


class DebtMFWidget(MFBaseWidget):
    def page_title(self): return "Debt Mutual Funds"
    def fund_category(self): return FUND_CATEGORY_DEBT
    def import_asset_type(self): return "mutual_fund"
    def import_fund_category(self): return FUND_CATEGORY_DEBT
    def supports_import(self): return True
