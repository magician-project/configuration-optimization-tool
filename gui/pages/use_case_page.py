"""
UseCasePage — tabbed view for a single use case.
Tabs: Questionnaire | Module Dashboard.

Workflow:
  1. Answer questionnaire → impacts/flags/confidence recomputed on every save.
  2. In Module Dashboard: Acknowledge flags → Validate → Compute → Deploy.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot

from app.models.use_case import UseCase, ComputeResult
from app.engine.questionnaire_engine import compute_impacts, apply_impacts_to_modules
from app.ros.ros2_adapter import get_adapter
from app.storage import json_store
from gui.components.confidence_bar import ConfidenceBar
from gui.components.questionnaire_form import QuestionnaireForm
from gui.components.module_grid import ModuleGrid
from gui.components.module_detail import ModuleDetail
from gui.components.compute_progress_dialog import ComputeProgressDialog
from app.engine.compute_runner import ComputeRunner

logger = logging.getLogger(__name__)


class UseCasePage(QWidget):
    navigate_home = Signal()

    def __init__(self, use_case_id: str, parent=None) -> None:
        super().__init__(parent)
        self._use_case_id = use_case_id
        self._use_case: Optional[UseCase] = None
        self._pending_answers: Optional[dict] = None
        self._dirty = False
        self._active_detail_dlg = None   # currently open ModuleDetail dialog
        self._build_ui()
        self._load()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setStyleSheet("background: #f0f2f5;")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 16, 28, 16)
        root.setSpacing(10)

        # Top navigation
        nav = QHBoxLayout()
        back_btn = QPushButton("All use cases")
        back_btn.setStyleSheet("border: none; color: #162759; font-weight: bold; background: transparent;")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self._go_home)
        nav.addWidget(back_btn)
        nav.addStretch()
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #162759;")
        nav.addWidget(self._title_lbl)
        root.addLayout(nav)

        # Status banner (hidden by default)
        self._banner = QLabel()
        self._banner.setStyleSheet(
            "background: #d1fae5; color: #065f46; padding: 6px 12px; border-radius: 4px;"
        )
        self._banner.hide()
        root.addWidget(self._banner)

        # Tabs
        self._tabs = QTabWidget()
        root.addWidget(self._tabs, stretch=1)

        # -- Questionnaire tab
        q_tab = QWidget()
        q_vbox = QVBoxLayout(q_tab)
        q_vbox.setContentsMargins(8, 8, 8, 8)
        q_vbox.setSpacing(8)
        self._confidence_bar = ConfidenceBar()
        q_vbox.addWidget(self._confidence_bar)
        self._form = QuestionnaireForm()
        self._form.answers_changed.connect(self._on_answers_changed)
        q_vbox.addWidget(self._form, stretch=1)

        # Save bar (shown only when dirty)
        self._save_bar = QWidget()
        self._save_bar.setStyleSheet(
            "background: #fffbeb; border-top: 1px solid #fcd34d;"
        )
        save_bar_layout = QHBoxLayout(self._save_bar)
        save_bar_layout.setContentsMargins(12, 6, 12, 6)
        save_bar_layout.setSpacing(12)
        unsaved_lbl = QLabel("You have unsaved changes.")
        unsaved_lbl.setStyleSheet("color: #92400e; font-size: 12px; background: transparent;")
        save_bar_layout.addWidget(unsaved_lbl)
        save_bar_layout.addStretch()
        discard_btn = QPushButton("Discard")
        discard_btn.setStyleSheet(
            "border: 1px solid #d1d5db; background: white; color: #374151; "
            "padding: 4px 14px; border-radius: 4px; font-size: 12px;"
        )
        discard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        discard_btn.clicked.connect(self._discard_changes)
        save_bar_layout.addWidget(discard_btn)
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            "background: #162759; color: white; padding: 4px 18px; "
            "border-radius: 4px; font-weight: bold; font-size: 12px; border: none;"
        )
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_questionnaire)
        save_bar_layout.addWidget(save_btn)
        self._save_bar.hide()
        q_vbox.addWidget(self._save_bar)

        # -- Module dashboard tab (added first so it is index 0)
        dash_tab = QWidget()
        dash_vbox = QVBoxLayout(dash_tab)
        dash_vbox.setContentsMargins(8, 8, 8, 8)
        dash_vbox.setSpacing(8)
        self._module_grid = ModuleGrid()
        self._module_grid.module_selected.connect(self._open_module_detail)
        dash_vbox.addWidget(self._module_grid, stretch=1)
        self._tabs.addTab(dash_tab, "Module Dashboard")

        # -- Questionnaire tab (index 1)
        self._tabs.addTab(q_tab, "Use Case Specification")
        self._tabs.currentChanged.connect(self._on_tab_changed)

    # ------------------------------------------------------------------
    # Load / refresh
    # ------------------------------------------------------------------

    def _load(self) -> None:
        uc = json_store.load(self._use_case_id)
        if uc is None:
            QMessageBox.critical(self, "Error", f"Use case '{self._use_case_id}' not found.")
            self.navigate_home.emit()
            return
        self._use_case = uc
        self._dirty = False
        self._pending_answers = None
        self._save_bar.hide()
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        uc = self._use_case
        self._title_lbl.setText(f"{uc.name}  <small style='color:#9ca3af;font-size:12px'>#{uc.id}</small>")
        self._title_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._confidence_bar.update_score(uc.confidence)
        self._form.load_answers(uc.answers.model_dump())
        self._module_grid.update_modules(uc.modules)

    # ------------------------------------------------------------------
    # Questionnaire save / dirty tracking
    # ------------------------------------------------------------------

    @Slot(dict)
    def _on_answers_changed(self, answers: dict) -> None:
        self._pending_answers = answers
        self._dirty = True
        self._save_bar.show()

    def _discard_changes(self) -> None:
        """Reload from disk, losing unsaved edits."""
        self._load()

    def _go_home(self) -> None:
        if self._dirty:
            reply = QMessageBox.question(
                self, "Unsaved changes",
                "You have unsaved changes to the questionnaire.\n"
                "Leave anyway and discard them?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Discard:
                return
        self.navigate_home.emit()

    def _on_tab_changed(self, index: int) -> None:
        """Warn when switching away from the questionnaire tab with unsaved changes."""
        if index != 1 and self._dirty:
            reply = QMessageBox.question(
                self, "Unsaved changes",
                "You have unsaved changes to the questionnaire.\n"
                "Switch tabs anyway and discard them?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Discard:
                # Switch back to questionnaire tab silently
                self._tabs.blockSignals(True)
                self._tabs.setCurrentIndex(1)
                self._tabs.blockSignals(False)
                return

    def _save_questionnaire(self) -> None:
        if self._pending_answers is None or self._use_case is None:
            return
        from app.models.questionnaire import QuestionnaireAnswers
        try:
            parsed = QuestionnaireAnswers(**self._pending_answers)
        except Exception:
            logger.exception("Failed to parse questionnaire answers")
            return

        self._use_case.answers = parsed
        self._use_case.updated_at = datetime.now(timezone.utc).isoformat()
        result = compute_impacts(parsed, module_answers=self._use_case.module_answers)
        apply_impacts_to_modules(self._use_case, result)
        json_store.save(self._use_case)

        self._dirty = False
        self._pending_answers = None
        self._save_bar.hide()
        self._confidence_bar.update_score(self._use_case.confidence)
        self._module_grid.update_modules(self._use_case.modules)

        needs = sum(1 for m in self._use_case.modules.values() if m.status == "needs_action")
        total = len(self._use_case.modules)
        self._show_banner(f"Saved — {needs} of {total} modules need action")

    def _show_banner(self, text: str) -> None:
        self._banner.setText(text)
        self._banner.show()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, self._banner.hide)

    # ------------------------------------------------------------------
    # Module actions
    # ------------------------------------------------------------------

    def _open_module_detail(self, module_id: str) -> None:
        if self._use_case is None:
            return
        ms = self._use_case.modules.get(module_id)
        if ms is None:
            return
        module_config = self._use_case.module_answers.get(module_id, {})
        dlg = ModuleDetail(ms, module_config=module_config, parent=self)
        dlg.action_requested.connect(self._handle_module_action)
        dlg.module_config_changed.connect(self._on_module_config_changed)
        self._active_detail_dlg = dlg
        dlg.exec()
        self._active_detail_dlg = None
        # Refresh grid in case compute/deploy changed state outside the dialog
        if self._use_case:
            self._module_grid.update_modules(self._use_case.modules)

    @Slot(str, dict)
    def _on_module_config_changed(self, module_id: str, config: dict) -> None:
        """Persist module-specific config and re-evaluate impacts."""
        if self._use_case is None:
            return
        self._use_case.module_answers[module_id] = config
        self._use_case.updated_at = datetime.now(timezone.utc).isoformat()
        result = compute_impacts(self._use_case.answers, module_answers=self._use_case.module_answers)
        apply_impacts_to_modules(self._use_case, result)
        json_store.save(self._use_case)
        self._module_grid.update_modules(self._use_case.modules)
        # Refresh the open dialog
        if self._active_detail_dlg:
            ms = self._use_case.modules.get(module_id)
            if ms:
                self._active_detail_dlg.refresh(ms)

    @Slot(str, str)
    def _handle_module_action(self, module_id: str, action: str) -> None:
        if action == "acknowledge":
            self._acknowledge_flags(module_id)
        elif action == "validate":
            self._validate_module(module_id)
        elif action == "compute":
            self._run_compute(module_id)
        elif action == "deploy":
            self._deploy_module(module_id)

    def _acknowledge_flags(self, module_id: str) -> None:
        uc = self._use_case
        if uc is None:
            return
        ms = uc.modules.get(module_id)
        if ms is None:
            return
        for f in ms.flags:
            f.acknowledged = True
        json_store.save(uc)
        self._module_grid.update_modules(uc.modules)
        if self._active_detail_dlg:
            self._active_detail_dlg.refresh(ms)

    def _validate_module(self, module_id: str) -> None:
        uc = self._use_case
        if uc is None:
            return
        ms = uc.modules.get(module_id)
        if ms is None:
            return
        unacked = [f for f in ms.flags if not f.acknowledged]
        if unacked:
            QMessageBox.warning(self, "Cannot validate", "All flags must be acknowledged first.")
            return
        ms.status = "validated"
        ms.validated_at = datetime.now(timezone.utc).isoformat()
        uc.updated_at = datetime.now(timezone.utc).isoformat()
        json_store.save(uc)
        self._module_grid.update_modules(uc.modules)
        if self._active_detail_dlg:
            self._active_detail_dlg.refresh(ms)

    def _run_compute(self, module_id: str) -> None:
        uc = self._use_case
        if uc is None:
            return
        ms = uc.modules.get(module_id)
        if ms is None:
            return

        ms.status = "computing"
        uc.updated_at = datetime.now(timezone.utc).isoformat()
        json_store.save(uc)
        self._module_grid.update_modules(uc.modules)
        if self._active_detail_dlg:
            self._active_detail_dlg.refresh(ms)

        from app.engine.module_registry import MODULES
        module_name = MODULES.get(module_id, {}).get("name", module_id)
        dlg = ComputeProgressDialog(module_name, parent=self)
        dlg.show()

        def on_line(line: str) -> None:
            dlg.append_line(line)

        def on_done(success: bool, result_path: str | None) -> None:
            dlg.on_done(success, result_path)
            if success and result_path:
                try:
                    with open(result_path, encoding="utf-8") as f:
                        data = json.load(f)
                    result = ComputeResult(**data)
                    json_store.save_compute_result(uc.id, result)
                    ms.status = "computed"
                    ms.compute_result = result
                    ms.computed_at = datetime.now(timezone.utc).isoformat()
                except Exception:
                    logger.exception("Failed to load compute result")
                    ms.status = "compute_failed"
            else:
                ms.status = "compute_failed"
            uc.updated_at = datetime.now(timezone.utc).isoformat()
            json_store.save(uc)
            self._module_grid.update_modules(uc.modules)
            if self._active_detail_dlg:
                self._active_detail_dlg.refresh(ms)

        runner = ComputeRunner(uc, module_id, on_line, on_done)
        runner.start()

    def _deploy_module(self, module_id: str) -> None:
        uc = self._use_case
        if uc is None:
            return
        ms = uc.modules.get(module_id)
        if ms is None:
            return
        if ms.compute_result is None:
            QMessageBox.warning(self, "Cannot deploy", "Run Compute first.")
            return

        ms.status = "deploying"
        uc.updated_at = datetime.now(timezone.utc).isoformat()
        json_store.save(uc)
        self._module_grid.update_modules(uc.modules)

        try:
            ros_interface_module = __import__(
                f"modules.{module_id}.ros_interface",
                fromlist=["get_commands"],
            )
            commands = ros_interface_module.get_commands(ms.compute_result.outputs)
        except Exception as exc:
            logger.exception("Failed to load ros_interface for %s", module_id)
            QMessageBox.critical(self, "Deploy error", f"Could not load ROS interface: {exc}")
            ms.status = "deploy_failed"
            json_store.save(uc)
            self._module_grid.update_modules(uc.modules)
            return

        adapter = get_adapter()
        result = adapter.apply_commands(module_id, commands)

        if result.get("success"):
            ms.status = "deployed"
            ms.deployed_at = datetime.now(timezone.utc).isoformat()
            self._show_banner(f"{ms.module_name} deployed to ROS 2.")
        else:
            ms.status = "deploy_failed"
            QMessageBox.warning(
                self, "Deploy failed",
                f"One or more ROS 2 commands failed. Check logs.\n{result}",
            )

        uc.updated_at = datetime.now(timezone.utc).isoformat()
        json_store.save(uc)
        self._module_grid.update_modules(uc.modules)
        if self._active_detail_dlg:
            self._active_detail_dlg.refresh(ms)
