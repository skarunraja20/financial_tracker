"""Stocks (NSE/BSE) widget."""

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QInputDialog,
)
from PyQt6.QtCore import Qt

from app.models import equity as equity_model
from app.core.security import encrypt_field, safe_decrypt_field
from app.core.session import session
from app.ui.base_asset_widget import BaseAssetWidget
from app.ui.widgets import (
    make_amount_spin, make_date_edit, make_combo,
    table_item, table_item_right, error_dialog,
)
from app.services.formatters import format_inr, format_date, format_gain
from app.core.constants import EXCHANGE_OPTIONS


class StocksWidget(BaseAssetWidget):
    def page_title(self): return "Stocks (NSE / BSE)"

    def table_headers(self):
        return ["Company", "Ticker", "Exchange", "Qty", "Avg Buy", "Current Price", "Invested", "Current Value", "Gain/Loss"]

    def load_data(self):
        return equity_model.get_all_stocks()

    def populate_row(self, table, row_idx, item):
        current_val = item["quantity"] * item["current_price"]
        gain_str = format_gain(current_val, item["purchase_value"])

        table.setItem(row_idx, 0, table_item(item["company_name"]))
        table.setItem(row_idx, 1, table_item(item["ticker_symbol"]))
        table.setItem(row_idx, 2, table_item(item["exchange"]))
        table.setItem(row_idx, 3, table_item_right(f"{item['quantity']:,.2f}"))
        table.setItem(row_idx, 4, table_item_right(f"₹{item['avg_buy_price']:,.2f}"))
        table.setItem(row_idx, 5, table_item_right(f"₹{item['current_price']:,.2f}"))
        table.setItem(row_idx, 6, table_item_right(format_inr(item["purchase_value"])))
        table.setItem(row_idx, 7, table_item_right(format_inr(current_val)))
        gain_item = table_item_right(gain_str)
        if current_val >= item["purchase_value"]:
            gain_item.setForeground(Qt.GlobalColor.green)
        else:
            gain_item.setForeground(Qt.GlobalColor.red)
        table.setItem(row_idx, 8, gain_item)

    def update_summary(self):
        total_invested = sum(i["purchase_value"] for i in self._items)
        total_current = sum(i["quantity"] * i["current_price"] for i in self._items)
        self.summary_label.setText(
            f"Total Value: <b>{format_inr(total_current)}</b>  |  "
            f"Invested: {format_inr(total_invested)}  |  "
            f"Gain/Loss: {format_gain(total_current, total_invested)}"
        )

    def open_add_dialog(self):
        dlg = StockDialog(parent=self)
        if dlg.exec():
            equity_model.add_stock(dlg.get_data())

    def open_edit_dialog(self, item):
        dlg = StockDialog(item, parent=self)
        if dlg.exec():
            equity_model.update_stock(item["id"], dlg.get_data())

    def delete_item(self, item):
        equity_model.delete_stock(item["id"])

    def _on_edit(self):
        item = self._selected_item()
        if item:
            new_price, ok = QInputDialog.getDouble(
                self, "Update Price",
                f"Current price for {item['ticker_symbol']}:",
                item["current_price"], 0.0, 1e9, 2,
            )
            if ok:
                equity_model.update_price(item["id"], new_price)
                self.refresh()
            else:
                self.open_edit_dialog(item)
                self.refresh()

    def supports_import(self): return True
    def import_asset_type(self): return "stock"


class StockDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stock")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.company = QLineEdit(data["company_name"] if data else "")
        self.company.setPlaceholderText("e.g. Reliance Industries")
        self.company.setMaxLength(150)
        form.addRow("Company Name*:", self.company)

        self.ticker = QLineEdit(data["ticker_symbol"] if data else "")
        self.ticker.setPlaceholderText("e.g. RELIANCE")
        self.ticker.setMaxLength(20)
        form.addRow("Ticker Symbol*:", self.ticker)

        self.exchange = make_combo(EXCHANGE_OPTIONS)
        if data:
            idx = self.exchange.findText(data["exchange"])
            if idx >= 0: self.exchange.setCurrentIndex(idx)
        form.addRow("Exchange*:", self.exchange)

        self.qty = make_amount_spin(prefix="")
        self.qty.setDecimals(2)
        if data: self.qty.setValue(data["quantity"])
        form.addRow("Quantity*:", self.qty)

        self.avg_price = make_amount_spin(max_val=1e8)
        if data: self.avg_price.setValue(data["avg_buy_price"])
        form.addRow("Avg Buy Price*:", self.avg_price)

        self.invested = make_amount_spin()
        if data: self.invested.setValue(data["purchase_value"])
        form.addRow("Total Invested*:", self.invested)

        self.current_price = make_amount_spin(max_val=1e8)
        if data: self.current_price.setValue(data["current_price"])
        form.addRow("Current Price*:", self.current_price)

        self.purchase_date = make_date_edit()
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["purchase_date"], "yyyy-MM-dd")
            if d.isValid(): self.purchase_date.setDate(d)
        form.addRow("Purchase Date*:", self.purchase_date)

        raw_demat = data.get("demat_account", "") if data else ""
        self.demat = QLineEdit(safe_decrypt_field(raw_demat, session.aes_key))
        self.demat.setPlaceholderText("Optional broker/demat reference")
        self.demat.setMaxLength(50)
        form.addRow("Demat Account:", self.demat)

        self.notes = QTextEdit(data.get("notes", "") if data else "")
        self.notes.setMaximumHeight(50)
        form.addRow("Notes:", self.notes)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self):
        if not self.company.text().strip() or not self.ticker.text().strip():
            error_dialog(self, "Validation", "Company name and ticker are required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "company_name": self.company.text().strip(),
            "ticker_symbol": self.ticker.text().strip().upper(),
            "exchange": self.exchange.currentText(),
            "quantity": self.qty.value(),
            "avg_buy_price": self.avg_price.value(),
            "purchase_value": self.invested.value(),
            "current_price": self.current_price.value(),
            "purchase_date": self.purchase_date.date().toString("yyyy-MM-dd"),
            "demat_account": encrypt_field(self.demat.text().strip(), session.aes_key) if session.aes_key else self.demat.text().strip(),
            "notes": self.notes.toPlainText().strip(),
        }
