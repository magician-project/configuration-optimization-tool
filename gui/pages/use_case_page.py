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

from app.models.use_case import UseCase, ComputeResult, ExternalSource
from app.engine.module_dependencies import validate_configuration
from app.engine.module_registry import is_assessed
from app.engine.questionnaire_engine import (
    compute_impacts, apply_impacts_to_modules, consumers_awaiting_external_input,
    sync_external_input_status,
)
from app.ros.ros2_adapter import get_adapter
from app.storage import json_store
from gui.components.confidence_bar import ConfidenceBar
from gui.components.external_inputs import ConfigurationValidationPanel
from gui.components.questionnaire_form import QuestionnaireForm
from gui.components.module_grid import ModuleGrid
from gui.components.module_detail import ModuleDetail
from gui.components.compute_progress_dialog import ComputeProgressDialog
from app.engine.compute_runner import ComputeRunner

logger = logging.getLogger(__name__)

# Modules whose compute.py always populates ComputeResult.deploy_blockers
# (as [] when there's nothing blocking). A stored result with
# deploy_blockers is None for one of these predates the convention and
# must be recomputed before deploy can trust it — see _deploy_module().
_MODULES_WITH_DEPLOY_BLOCKERS = {"localiser"}


class UseCasePage(QWidget):
    navigate_home = Signal()
    _compute_line_received = Signal(str)
    _compute_finished = Signal(str, bool, object)

    def __init__(self, use_case_id: str, parent=None) -> None:
        super().__init__(parent)
        self._use_case_id = use_case_id
        self._use_case: Optional[UseCase] = None
        self._pending_answers: Optional[dict] = None
        self._dirty = False
        self._active_detail_dlg = None   # currently open ModuleDetail dialog
        self._compute_progress_dlg: Optional[ComputeProgressDialog] = None
        self._compute_line_received.connect(self._append_compute_line)
        self._compute_finished.connect(self._finish_compute)
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
        self._form.help_link_requested.connect(self._open_module_detail)
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
        self._validation_panel = ConfigurationValidationPanel()
        self._validation_panel.configure_requested.connect(self._open_module_detail)
        self._validation_panel.specification_requested.connect(lambda: self._tabs.setCurrentIndex(1))
        dash_vbox.addWidget(self._validation_panel)
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
        self._refresh_grid()

    def _refresh_grid(self) -> None:
        """Push the current module states and configuration validation to the dashboard."""
        uc = self._use_case
        if uc is None:
            return
        self._module_grid.update_modules(uc.modules)
        self._validation_panel.update_validation(self._validation(uc))

    @staticmethod
    def _validation(uc: UseCase):
        return validate_configuration(uc.answers.q_pipeline, uc.answers.q3_additional_sensors, uc.external_sources)

    def _refresh_open_dialog(self, module_id: str) -> None:
        """Push the latest ModuleState + external inputs into the open detail dialog, if any."""
        if self._use_case is None or self._active_detail_dlg is None:
            return
        ms = self._use_case.modules.get(module_id)
        if ms:
            self._active_detail_dlg.refresh(ms, external_inputs=self._external_inputs_for(module_id))

    def _external_inputs_for(self, module_id: str) -> list:
        return [r for r in self._validation(self._use_case).external_inputs if r.consumer == module_id]

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
        self._refresh_grid()

        needs = sum(1 for m in self._use_case.modules.values() if m.status == "needs_action")
        total = len(self._use_case.modules)
        if not is_assessed(parsed.q_pipeline):
            self._show_banner("Saved — choose a pipeline selection to assess the modules")
            return
        self._show_banner(f"Saved — {needs} of {total} modules need action")

    def _show_banner(self, text: str) -> None:
        self._banner.setText(text)
        self._banner.show()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, self._banner.hide)

    # ------------------------------------------------------------------
    # Module actions
    # ------------------------------------------------------------------

    def _open_module_detail(self, module_id: str, doc_anchor: Optional[str] = None) -> None:
        if self._use_case is None:
            return
        ms = self._use_case.modules.get(module_id)
        if ms is None:
            return
        module_config = self._use_case.module_answers.get(module_id, {})
        dlg = ModuleDetail(
            ms, module_config=module_config,
            external_inputs=self._external_inputs_for(module_id), parent=self,
        )
        if doc_anchor is not None:
            dlg.show_documentation(doc_anchor)
        dlg.action_requested.connect(self._handle_module_action)
        dlg.module_config_changed.connect(self._on_module_config_changed)
        dlg.external_source_changed.connect(self._on_external_source_changed)
        self._active_detail_dlg = dlg
        dlg.exec()
        self._active_detail_dlg = None
        # Refresh grid in case compute/deploy changed state outside the dialog
        if self._use_case:
            self._refresh_grid()

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
        self._refresh_grid()
        self._refresh_open_dialog(module_id)

    @Slot(str, dict)
    def _on_external_source_changed(self, dependency_id: str, source: dict) -> None:
        """Persist the partner's external source for an input requirement."""
        uc = self._use_case
        if uc is None:
            return
        uc.external_sources[dependency_id] = ExternalSource(**source)
        sync_external_input_status(uc)
        uc.updated_at = datetime.now(timezone.utc).isoformat()
        json_store.save(uc)
        self._refresh_grid()
        for req in self._validation(uc).external_inputs:
            if req.dependency_id == dependency_id:
                self._refresh_open_dialog(req.consumer)

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
        newly_acked = sum(1 for f in ms.flags if not f.acknowledged)
        for f in ms.flags:
            f.acknowledged = True
        json_store.save(uc)
        self._refresh_grid()
        self._refresh_open_dialog(module_id)
        if newly_acked:
            flag_word = "flag" if newly_acked == 1 else "flags"
            self._show_banner(
                f"{newly_acked} {flag_word} acknowledged for {ms.module_name}. "
                "You can now mark the module as validated."
            )

    def _validate_module(self, module_id: str) -> None:
        uc = self._use_case
        if uc is None:
            return
        ms = uc.modules.get(module_id)
        if ms is None or ms.status in ("out_of_scope", "not_assessed"):
            return
        if module_id in consumers_awaiting_external_input(uc):
            reply = QMessageBox.question(
                self, "External input not agreed",
                "This module still needs an external input source with an agreed contract.\n"
                "Mark it as validated anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        unacked = [f for f in ms.flags if not f.acknowledged]
        if unacked:
            QMessageBox.warning(self, "Cannot validate", "All flags must be acknowledged first.")
            return
        ms.status = "validated"
        ms.validated_at = datetime.now(timezone.utc).isoformat()
        uc.updated_at = datetime.now(timezone.utc).isoformat()
        json_store.save(uc)
        self._refresh_grid()
        self._refresh_open_dialog(module_id)

    def _run_compute(self, module_id: str) -> None:
        uc = self._use_case
        if uc is None:
            return
        ms = uc.modules.get(module_id)
        if ms is None or ms.status == "out_of_scope":
            return

        ms.status = "computing"
        uc.updated_at = datetime.now(timezone.utc).isoformat()
        json_store.save(uc)
        self._refresh_grid()
        self._refresh_open_dialog(module_id)

        from app.engine.module_registry import MODULES
        module_name = MODULES.get(module_id, {}).get("name", module_id)
        dlg = ComputeProgressDialog(module_name, parent=self)
        self._compute_progress_dlg = dlg
        dlg.show()

        def on_line(line: str) -> None:
            self._compute_line_received.emit(line)

        def on_done(success: bool, result_path: str | None) -> None:
            self._compute_finished.emit(module_id, success, result_path)

        runner = ComputeRunner(uc, module_id, on_line, on_done)
        runner.start()

    @Slot(str)
    def _append_compute_line(self, line: str) -> None:
        if self._compute_progress_dlg is not None:
            self._compute_progress_dlg.append_line(line)

    @Slot(str, bool, object)
    def _finish_compute(
        self, module_id: str, success: bool, result_path: str | None
    ) -> None:
        uc = self._use_case
        if uc is None:
            return
        ms = uc.modules.get(module_id)
        if ms is None:
            return

        if self._compute_progress_dlg is not None:
            self._compute_progress_dlg.on_done(success, result_path)

        # Scope may have changed while compute ran; a late result must not undo that.
        if ms.status in ("out_of_scope", "not_assessed"):
            return

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
        self._refresh_grid()
        self._refresh_open_dialog(module_id)

    def _deploy_module(self, module_id: str) -> None:
        uc = self._use_case
        if uc is None:
            return
        ms = uc.modules.get(module_id)
        if ms is None or ms.status == "out_of_scope":
            return
        if ms.compute_result is None:
            QMessageBox.warning(self, "Cannot deploy", "Run Compute first.")
            return

        # Generic hook: any module can mark its own configuration as not
        # deployable yet via ComputeResult.deploy_blockers (see
        # modules/localiser/compute.py). None means "never evaluated" --
        # for modules known to populate it, that means a stale pre-upgrade
        # result, so force a recompute instead of silently allowing deploy.
        blockers = ms.compute_result.deploy_blockers
        if blockers is None and module_id in _MODULES_WITH_DEPLOY_BLOCKERS:
            QMessageBox.warning(
                self, "Cannot deploy",
                f"This {ms.module_name} result predates deployment validation. "
                "Run Compute again.",
            )
            return
        blockers = blockers or []
        if blockers:
            QMessageBox.warning(
                self, "Deployment blocked",
                f"{ms.module_name} configuration is not ready to deploy:\n- "
                + "\n- ".join(blockers),
            )
            return

        ms.status = "deploying"
        uc.updated_at = datetime.now(timezone.utc).isoformat()
        json_store.save(uc)
        self._refresh_grid()

        try:
            ros_interface_module = __import__(
                f"modules.{module_id}.ros_interface",
                fromlist=["get_commands"],
            )
            commands = ros_interface_module.get_commands(ms.compute_result.interface_outputs())
        except Exception as exc:
            logger.exception("Failed to load ros_interface for %s", module_id)
            QMessageBox.critical(self, "Deploy error", f"Could not load ROS interface: {exc}")
            ms.status = "deploy_failed"
            json_store.save(uc)
            self._refresh_grid()
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
        self._refresh_grid()
        self._refresh_open_dialog(module_id)
