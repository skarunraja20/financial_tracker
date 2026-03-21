"""
Goals feature UI — FinBoom-style goal cards with progress bars + asset tagging.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QDialog, QLineEdit,
    QDoubleSpinBox, QComboBox, QCheckBox, QDialogButtonBox,
    QDateEdit, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QSizePolicy, QMessageBox,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QPainter, QColor

from app.ui.widgets import (
    title_label, separator, field_label, confirm_delete,
    info_dialog, error_dialog, make_amount_spin, make_date_edit,
)
from app.models import goals as goals_model
from app.services.formatters import format_inr
from app.core.constants import (
    GOAL_COLORS, GOAL_ICONS, ASSET_TYPE_LABELS,
)


# ── Asset allocation bar ──────────────────────────────────────────────────────

class AllocationBar(QWidget):
    """Horizontal stacked bar showing debt/equity/gold/real-estate breakdown."""

    _SEGMENTS = [
        ("debt",        "#3b82f6", "Debt"),
        ("equity",      "#10b981", "Equity"),
        ("gold",        "#f59e0b", "Gold"),
        ("real_estate", "#f97316", "Real Estate"),
    ]

    def __init__(self, allocation: dict, parent=None):
        super().__init__(parent)
        self._alloc = allocation
        self.setFixedHeight(8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = self._alloc.get("total", 0.0)
        w, h = self.width(), self.height()
        radius = h // 2

        if total <= 0:
            painter.setBrush(QColor("#334155"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, w, h, radius, radius)
            return

        # Calculate segment widths
        segs = []
        for key, color, _ in self._SEGMENTS:
            val = self._alloc.get(key, 0.0)
            if val > 0:
                segs.append((int(val / total * w), QColor(color)))

        # Distribute any rounding remainder to the last segment
        total_assigned = sum(s[0] for s in segs)
        if segs and total_assigned < w:
            segs[-1] = (segs[-1][0] + (w - total_assigned), segs[-1][1])

        painter.setPen(Qt.PenStyle.NoPen)
        x = 0
        for i, (seg_w, color) in enumerate(segs):
            painter.setBrush(color)
            if len(segs) == 1:
                painter.drawRoundedRect(x, 0, seg_w, h, radius, radius)
            elif i == 0:
                # Left-rounded only
                painter.drawRoundedRect(x, 0, seg_w, h, radius, radius)
                painter.drawRect(x + radius, 0, seg_w - radius, h)
            elif i == len(segs) - 1:
                # Right-rounded only
                painter.drawRoundedRect(x, 0, seg_w, h, radius, radius)
                painter.drawRect(x, 0, seg_w - radius, h)
            else:
                painter.drawRect(x, 0, seg_w, h)
            x += seg_w


# ── Goals widget (main page) ───────────────────────────────────────────────────

class GoalsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("goalsWidget")
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        self._main = QVBoxLayout(content)
        self._main.setContentsMargins(24, 24, 24, 24)
        self._main.setSpacing(20)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        lbl = title_label("Goals")
        lbl.setObjectName("titleLabel")
        header.addWidget(lbl)
        header.addStretch()

        self.btn_new = QPushButton("+ New Goal")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.setFixedHeight(36)
        self.btn_new.clicked.connect(self._add_goal)
        header.addWidget(self.btn_new)

        self._main.addLayout(header)

        sub = QLabel("Track financial milestones and see how your assets contribute to each goal.")
        sub.setObjectName("subtitle")
        self._main.addWidget(sub)
        self._main.addWidget(separator())

        # ── Summary bar ───────────────────────────────────────────────────────
        self._summary_frame = QFrame()
        self._summary_frame.setObjectName("chartFrame")
        self._summary_frame.setMinimumHeight(90)
        self._summary_layout = QHBoxLayout(self._summary_frame)
        self._summary_layout.setContentsMargins(28, 18, 28, 18)
        self._summary_layout.setSpacing(0)
        self._main.addWidget(self._summary_frame)

        # ── Goals grid ────────────────────────────────────────────────────────
        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(16)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._main.addWidget(self._grid_widget)

        self._main.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def refresh(self):
        # Clear grid
        for i in reversed(range(self._grid.count())):
            item = self._grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        goals = goals_model.get_all_goals_with_progress()

        # Update summary bar
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_target = sum(g["target_amount"] for g in goals)
        total_current = sum(g["current_amount"] for g in goals)
        overall_pct = (total_current / total_target * 100) if total_target > 0 else 0

        for label, value, color in [
            ("TOTAL GOALS", str(len(goals)), "#14b8a6"),
            ("TOTAL TARGET", format_inr(total_target), "#f59e0b"),
            ("TOTAL ACHIEVED", format_inr(total_current), "#10b981"),
            ("OVERALL PROGRESS", f"{overall_pct:.1f}%",
             "#10b981" if overall_pct >= 50 else "#f59e0b"),
        ]:
            cell_widget = QWidget()
            cell_widget.setMinimumWidth(160)
            cell_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            cell = QVBoxLayout(cell_widget)
            cell.setSpacing(4)
            cell.setContentsMargins(0, 0, 0, 0)
            l = QLabel(label)
            l.setStyleSheet(
                "color: #94a3b8; font-size: 8pt; letter-spacing: 1px; background: transparent;"
            )
            v = QLabel(value)
            v.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
            v.setStyleSheet(f"color: {color}; background: transparent;")
            v.setWordWrap(False)
            cell.addWidget(l)
            cell.addWidget(v)
            self._summary_layout.addWidget(cell_widget)

        if not goals:
            empty = QLabel("No goals yet. Click '+ New Goal' to create your first financial goal.")
            empty.setObjectName("subtitle")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(empty, 0, 0)
            return

        # Build 2-column grid of goal cards
        col_count = 2
        for idx, goal in enumerate(goals):
            card = self._build_goal_card(goal)
            self._grid.addWidget(card, idx // col_count, idx % col_count)

    def _build_goal_card(self, goal: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("goalCard")
        card.setMinimumHeight(300)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        # ── Top row: icon + name + actions ────────────────────────────────────
        top = QHBoxLayout()

        icon_lbl = QLabel(goal.get("icon", "🎯"))
        icon_lbl.setFont(QFont("Segoe UI", 18))
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = goal.get("color", "#14b8a6")
        icon_lbl.setStyleSheet(
            f"background-color: {color}22; border-radius: 10px; padding: 2px;"
        )
        top.addWidget(icon_lbl)

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name_lbl = QLabel(goal["name"])
        name_lbl.setObjectName("goalName")
        name_col.addWidget(name_lbl)

        if goal.get("deadline"):
            dl = QLabel(f"Target date: {goal['deadline'][:10]}")
            dl.setObjectName("goalProgress")
            name_col.addWidget(dl)
        top.addLayout(name_col)
        top.addStretch()

        # Edit / Delete buttons
        btn_edit = QPushButton("✏")
        btn_edit.setFixedSize(30, 30)
        btn_edit.setObjectName("secondaryButton")
        btn_edit.setToolTip("Edit goal")
        gid = goal["id"]
        btn_edit.clicked.connect(lambda _, g=goal: self._edit_goal(g))

        btn_del = QPushButton("🗑")
        btn_del.setFixedSize(30, 30)
        btn_del.setObjectName("dangerButton")
        btn_del.setToolTip("Delete goal")
        btn_del.clicked.connect(lambda _, g=goal: self._delete_goal(g))

        top.addWidget(btn_edit)
        top.addWidget(btn_del)
        layout.addLayout(top)

        # ── Amounts ───────────────────────────────────────────────────────────
        current = goal["current_amount"]
        target = goal["target_amount"]
        pct = goal["percentage"]

        amt_row = QHBoxLayout()
        cur_lbl = QLabel(format_inr(current))
        cur_lbl.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        cur_lbl.setStyleSheet(f"color: {color};")

        of_lbl = QLabel(f" of {format_inr(target)}")
        of_lbl.setObjectName("goalProgress")

        amt_row.addWidget(cur_lbl)
        amt_row.addWidget(of_lbl)
        amt_row.addStretch()

        pct_lbl = QLabel(f"{pct:.1f}%")
        pct_lbl.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        pct_lbl.setStyleSheet(
            f"color: {'#10b981' if pct >= 100 else color};"
        )
        amt_row.addWidget(pct_lbl)
        layout.addLayout(amt_row)

        # ── Progress bar ──────────────────────────────────────────────────────
        track = QFrame()
        track.setObjectName("progressTrack")
        track.setFixedHeight(10)
        track.setStyleSheet("border-radius: 5px; background-color: #334155;")

        fill_pct = min(pct, 100)
        fill = QFrame(track)
        fill.setObjectName("progressFill")
        fill.setFixedHeight(10)
        fill.setStyleSheet(
            f"background-color: {'#10b981' if pct >= 100 else color}; border-radius: 5px;"
        )
        # We'll use a proportional approach via resizeEvent simulation
        # Store fill widget ref on track
        track._fill = fill
        track._pct = fill_pct
        track.resizeEvent = lambda e, t=track: self._resize_fill(e, t)
        layout.addWidget(track)

        # ── Asset allocation bar ──────────────────────────────────────────────
        alloc = goal.get("allocation", {})
        alloc_total = alloc.get("total", 0.0)

        alloc_title = QLabel("Asset Allocation")
        alloc_title.setStyleSheet(
            "color: #64748b; font-size: 9.5pt; letter-spacing: 1px; background: transparent;"
        )
        layout.addWidget(alloc_title)

        alloc_bar = AllocationBar(alloc)
        layout.addWidget(alloc_bar)

        # Legend row
        legend = QHBoxLayout()
        legend.setSpacing(10)
        if alloc_total > 0:
            for key, seg_color, label in AllocationBar._SEGMENTS:
                val = alloc.get(key, 0.0)
                if val <= 0:
                    continue
                pct = val / alloc_total * 100
                dot = QLabel("●")
                dot.setStyleSheet(f"color: {seg_color}; font-size: 12px; background: transparent;")
                dot.setFixedWidth(14)
                txt = QLabel(f"{label} {pct:.0f}%")
                txt.setStyleSheet("color: #64748b; font-size: 10.5pt; background: transparent;")
                legend.addWidget(dot)
                legend.addWidget(txt)
        else:
            none_lbl = QLabel("No assets tagged yet")
            none_lbl.setStyleSheet("color: #64748b; font-size: 10.5pt; background: transparent;")
            legend.addWidget(none_lbl)
        legend.addStretch()
        layout.addLayout(legend)

        # ── Asset count + Tag button ──────────────────────────────────────────
        bot = QHBoxLayout()
        assets_lbl = QLabel(f"{goal['tagged_count']} asset(s) tagged")
        assets_lbl.setObjectName("goalProgress")
        bot.addWidget(assets_lbl)
        bot.addStretch()

        btn_tag = QPushButton("Tag Assets")
        btn_tag.setObjectName("secondaryButton")
        btn_tag.setFixedHeight(28)
        btn_tag.clicked.connect(lambda _, g=goal: self._tag_assets(g))
        bot.addWidget(btn_tag)
        layout.addLayout(bot)

        if goal.get("description"):
            desc = QLabel(goal["description"])
            desc.setObjectName("goalProgress")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        return card

    @staticmethod
    def _resize_fill(event, track: QFrame):
        """Dynamically resize the fill bar based on track width."""
        if not hasattr(track, "_fill"):
            return
        w = track.width()
        fill_w = max(int(w * track._pct / 100), 0)
        track._fill.setFixedWidth(fill_w)
        track._fill.setFixedHeight(10)
        track._fill.move(0, 0)

    # ── Goal CRUD actions ─────────────────────────────────────────────────────

    def _add_goal(self):
        dlg = GoalDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            goals_model.add_goal(**data)
            self.refresh()

    def _edit_goal(self, goal: dict):
        dlg = GoalDialog(goal=goal, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            goals_model.update_goal(goal["id"], **data)
            self.refresh()

    def _delete_goal(self, goal: dict):
        if confirm_delete(self, goal["name"]):
            goals_model.delete_goal(goal["id"])
            self.refresh()

    def _tag_assets(self, goal: dict):
        dlg = TagAssetsDialog(goal, parent=self)
        if dlg.exec():
            selected = dlg.get_selected()
            goals_model.set_tagged_assets(goal["id"], selected)
            self.refresh()


# ── Goal add/edit dialog ───────────────────────────────────────────────────────

class GoalDialog(QDialog):
    def __init__(self, goal: dict | None = None, parent=None):
        super().__init__(parent)
        self._goal = goal
        self.setWindowTitle("Edit Goal" if goal else "New Goal")
        self.setMinimumWidth(440)
        self._build_ui()
        if goal:
            self._populate(goal)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        layout.addWidget(QLabel(
            "<b>Edit Goal</b>" if self._goal else "<b>Create a New Goal</b>"
        ))
        layout.addWidget(separator())

        def row(lbl_text, widget):
            r = QHBoxLayout()
            lbl = field_label(lbl_text)
            lbl.setFixedWidth(110)
            r.addWidget(lbl)
            r.addWidget(widget)
            layout.addLayout(r)

        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Retirement Fund, House Down Payment")
        row("Goal Name *", self.name_edit)

        # Target amount
        self.target_spin = make_amount_spin(min_val=1.0, max_val=1e13)
        self.target_spin.setSingleStep(50_000)
        row("Target Amount *", self.target_spin)

        # Description
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Short description (optional)")
        row("Description", self.desc_edit)

        # Icon
        self.icon_combo = QComboBox()
        for ic in GOAL_ICONS:
            self.icon_combo.addItem(ic, ic)
        row("Icon", self.icon_combo)

        # Color
        self.color_combo = QComboBox()
        for c in GOAL_COLORS:
            self.color_combo.addItem(c, c)
        row("Color", self.color_combo)

        # Deadline (optional)
        self.deadline_check = QCheckBox("Set a target deadline")
        self.deadline_edit = make_date_edit()
        self.deadline_edit.setDate(QDate.currentDate().addYears(5))
        self.deadline_edit.setEnabled(False)
        self.deadline_check.stateChanged.connect(
            lambda s: self.deadline_edit.setEnabled(bool(s))
        )
        layout.addWidget(self.deadline_check)
        layout.addWidget(self.deadline_edit)

        layout.addWidget(separator())

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._validate_and_accept)
        btns.rejected.connect(self.reject)
        # Style OK button
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setObjectName("primaryButton")
        ok_btn.setText("Save Goal")
        layout.addWidget(btns)

    def _populate(self, goal: dict):
        self.name_edit.setText(goal.get("name", ""))
        self.target_spin.setValue(float(goal.get("target_amount", 0)))
        self.desc_edit.setText(goal.get("description", "") or "")

        icon = goal.get("icon", "🎯")
        idx = self.icon_combo.findData(icon)
        if idx >= 0:
            self.icon_combo.setCurrentIndex(idx)

        color = goal.get("color", "#14b8a6")
        idx = self.color_combo.findData(color)
        if idx >= 0:
            self.color_combo.setCurrentIndex(idx)

        if goal.get("deadline"):
            self.deadline_check.setChecked(True)
            try:
                d = QDate.fromString(goal["deadline"][:10], "yyyy-MM-dd")
                self.deadline_edit.setDate(d)
            except Exception:
                pass

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            error_dialog(self, "Validation Error", "Goal name is required.")
            return
        if self.target_spin.value() <= 0:
            error_dialog(self, "Validation Error", "Target amount must be greater than 0.")
            return
        self.accept()

    def get_data(self) -> dict:
        deadline = None
        if self.deadline_check.isChecked():
            deadline = self.deadline_edit.date().toString("yyyy-MM-dd")
        return {
            "name": self.name_edit.text().strip(),
            "target_amount": self.target_spin.value(),
            "description": self.desc_edit.text().strip(),
            "icon": self.icon_combo.currentData(),
            "color": self.color_combo.currentData(),
            "deadline": deadline,
        }


# ── Tag Assets dialog ──────────────────────────────────────────────────────────

class TagAssetsDialog(QDialog):
    """
    Shows all available assets grouped by category with checkboxes.
    User checks/unchecks which assets contribute to this goal.
    """

    def __init__(self, goal: dict, parent=None):
        super().__init__(parent)
        self._goal = goal
        self.setWindowTitle(f"Tag Assets — {goal['name']}")
        self.setMinimumSize(580, 660)
        self.resize(600, 700)
        self._checkboxes: list[tuple[str, int, QCheckBox]] = []  # (asset_type, asset_id, cb)
        self._build_ui()
        self._load_assets()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        hdr = QHBoxLayout()
        icon_lbl = QLabel(self._goal.get("icon", "🎯"))
        icon_lbl.setFont(QFont("Segoe UI", 16))
        hdr.addWidget(icon_lbl)
        title = QLabel(f"<b>{self._goal['name']}</b>  —  Target: {format_inr(self._goal['target_amount'])}")
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        sub = QLabel(
            "Select which assets count towards this goal. "
            "Their current values will be summed to track progress."
        )
        sub.setObjectName("goalProgress")
        sub.setWordWrap(True)
        layout.addWidget(sub)
        layout.addWidget(separator())

        # Scroll area for asset groups — expands to fill dialog
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._asset_container = QWidget()
        self._asset_layout = QVBoxLayout(self._asset_container)
        self._asset_layout.setSpacing(10)
        self._asset_layout.setContentsMargins(6, 6, 6, 6)
        scroll.setWidget(self._asset_container)
        layout.addWidget(scroll, stretch=1)

        layout.addWidget(separator())

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setObjectName("primaryButton")
        ok_btn.setText("Save Tags")
        layout.addWidget(btns)

    def _load_assets(self):
        assets = goals_model.get_all_assets_for_tagging(self._goal["id"])

        if not assets:
            empty = QLabel("No assets found. Add assets first, then tag them to goals.")
            empty.setObjectName("subtitle")
            self._asset_layout.addWidget(empty)
            return

        for asset_type, items in assets.items():
            if not items:
                continue

            # Section title label (no QGroupBox — avoids floating-title overlap)
            label_text = ASSET_TYPE_LABELS.get(asset_type, asset_type)
            sec_lbl = QLabel(label_text)
            sec_lbl.setObjectName("settingsCardTitle")
            self._asset_layout.addWidget(sec_lbl)

            # Card frame for checkboxes
            group = QFrame()
            group.setObjectName("settingsCard")
            grp_layout = QVBoxLayout(group)
            grp_layout.setSpacing(6)
            grp_layout.setContentsMargins(14, 10, 14, 10)

            for item in items:
                cb = QCheckBox(
                    f"{item['name']}  ({format_inr(item['current_value'])})"
                )
                cb.setChecked(item["is_tagged"])
                grp_layout.addWidget(cb)
                self._checkboxes.append((asset_type, item["id"], cb))

            self._asset_layout.addWidget(group)

        self._asset_layout.addStretch()

    def get_selected(self) -> list[tuple]:
        """Return list of (asset_type, asset_id) that are checked."""
        return [
            (at, aid) for at, aid, cb in self._checkboxes if cb.isChecked()
        ]
