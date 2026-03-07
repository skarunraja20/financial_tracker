"""Equity Mutual Funds widget."""
from app.ui.mf_base_widget import MFBaseWidget
from app.core.constants import FUND_CATEGORY_EQUITY


class EquityMFWidget(MFBaseWidget):
    def page_title(self): return "Equity Mutual Funds"
    def fund_category(self): return FUND_CATEGORY_EQUITY
    def supports_import(self): return True
    def import_asset_type(self): return "mutual_fund"
    def import_fund_category(self): return FUND_CATEGORY_EQUITY
