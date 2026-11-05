"""Experiment schedules, pilot calibration, and per-trial CSV recording."""

import csv
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from reader_ui import COMMANDS, COMMAND_LABELS


APP_DIR = Path(__file__).resolve().parent
TRIAL_COLUMNS = (
    "trial_id",
    "experiment",
    "condition",
    "lighting",
    "threshold_level",
    "threshold_value",
    "target_zone",
    "target_command",
    "triggered_zone",
    "triggered_command",
    "correct",
    "motion_ratio",
    "trigger_time_ms",
    "false_trigger",
    "missed_trigger",
    "repetition",
    "notes",
    "started_at",
    "completed_at",
)


@dataclass
class Trial:
    number: int
    experiment_id: str
    experiment_name: str
    target_zone: str
    lighting: str
    threshold_level: str
    threshold_value: float
    repetition: int

    @property
    def trial_id(self) -> str:
        prefix = {"experiment1": "E1", "experiment2": "E2", "experiment3": "E3"}[self.experiment_id]
        return "{}-{:03d}".format(prefix, self.number)

    @property
    def target_command(self) -> str:
        return COMMANDS[self.target_zone]


def build_trial_schedule(experiment_id: str, baseline_threshold: float, threshold_levels: Optional[Dict[str, float]] = None) -> List[Trial]:
    """Construct the 30, 27, or 18 required trials in the assignment plan."""
    trials: List[Trial] = []
    if experiment_id == "experiment1":
        for zone in ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6"):
            for repetition in range(1, 6):
                trials.append(Trial(0, experiment_id, "Experiment 1 - Basic Accuracy", zone, "Normal Lighting", "Baseline", baseline_threshold, repetition))
        random.shuffle(trials)
    elif experiment_id == "experiment2":
        if not threshold_levels or not all(level in threshold_levels for level in ("Low", "Medium", "High")):
            raise ValueError("請先依 Pilot 結果設定 Low、Medium、High 三組門檻")
        for zone in ("Z1", "Z2", "Z3"):
            for level in ("Low", "Medium", "High"):
                for repetition in range(1, 4):
                    trials.append(Trial(0, experiment_id, "Experiment 2 - Threshold", zone, "Normal Lighting", level, threshold_levels[level], repetition))
        random.shuffle(trials)
    elif experiment_id == "experiment3":
        conditions = ["Normal Lighting", "Dim Lighting"]
        random.shuffle(conditions)
        for lighting in conditions:
            condition_trials = []
            for zone in ("Z1", "Z2", "Z3"):
                for repetition in range(1, 4):
                    condition_trials.append(Trial(0, experiment_id, "Experiment 3 - Lighting", zone, lighting, "Baseline", baseline_threshold, repetition))
            random.shuffle(condition_trials)
            trials.extend(condition_trials)
    else:
        raise ValueError("未知的實驗代碼：{}".format(experiment_id))
    for number, trial in enumerate(trials, start=1):
        trial.number = number
    return trials


class ExperimentRecorder:
    """Write experiment rows immediately so each completed trial is preserved."""

    def __init__(self) -> None:
        self.results_dir = APP_DIR / "results"
        self.pilot_dir = APP_DIR / "pilot-data"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.pilot_dir.mkdir(parents=True, exist_ok=True)
        self.experiment_path: Optional[Path] = None
        self.pilot_path = self.pilot_dir / "pilot-motion-ratios.csv"

    def start_experiment(self, experiment_id: str) -> Path:
        timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
        self.experiment_path = self.results_dir / "{}_{}.csv".format(experiment_id, timestamp)
        return self.experiment_path

    def record_trial(self, row: Dict[str, object]) -> None:
        if self.experiment_path is None:
            raise RuntimeError("尚未啟動實驗記錄")
        self._append(self.experiment_path, TRIAL_COLUMNS, row)

    def record_pilot(self, zone: str, ratio: float, threshold: float) -> None:
        columns = ("timestamp", "lighting", "triggered_zone", "triggered_command", "motion_ratio", "threshold_value")
        row = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "lighting": "Normal Lighting",
            "triggered_zone": zone,
            "triggered_command": COMMANDS[zone],
            "motion_ratio": "{:.6f}".format(ratio),
            "threshold_value": "{:.6f}".format(threshold),
        }
        self._append(self.pilot_path, columns, row)

    @staticmethod
    def _append(path: Path, columns: Sequence[str], row: Dict[str, object]) -> None:
        file_exists = path.exists() and path.stat().st_size > 0
        with path.open("a", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)


class ExperimentRunnerWindow:
    """Tkinter experiment helper driven by actual camera trigger events."""

    EXPERIMENT_CHOICES = (
        ("Pilot Calibration", "pilot"),
        ("Experiment 1 - Basic Accuracy (30 trials)", "experiment1"),
        ("Experiment 2 - Threshold Test (27 trials)", "experiment2"),
        ("Experiment 3 - Lighting Test (18 trials)", "experiment3"),
    )

    def __init__(self, app) -> None:
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.title("HW4 Experiment Runner")
        self.window.geometry("950x690")
        self.window.minsize(800, 600)
        self.recorder = ExperimentRecorder()
        self.choice_by_label = {label: code for label, code in self.EXPERIMENT_CHOICES}
        self.active_experiment_id: Optional[str] = None
        self.active_experiment_name = ""
        self.trials: List[Trial] = []
        self.active_trial: Optional[Trial] = None
        self.trial_started_at = 0.0
        self.trial_started_label = ""
        self.max_target_motion = 0.0
        self.completed_count = 0
        self.session_total = 0
        self.correct_count = 0
        self.false_count = 0
        self.missed_count = 0
        self.session_baseline_threshold = self.app.detector.threshold
        self.threshold_levels: Dict[str, float] = {}
        self.threshold_locked = False
        self.pilot_active = False
        self.pilot_values: List[float] = []
        self.timeout_after_id: Optional[str] = None
        self.session_started_at = ""
        self.saved_lighting_evidence = set()

        self.selection_var = tk.StringVar(value=self.EXPERIMENT_CHOICES[0][0])
        self.instruction_var = tk.StringVar(value="Pilot 不計入 75 次正式試驗。請先在正常光線下，以平常操作方式移動並觸發操作區；收集數值後再據此設定三組門檻。")
        self.trial_var = tk.StringVar(value="尚未開始試驗")
        self.condition_var = tk.StringVar(value="等待開始")
        self.progress_var = tk.StringVar(value="已完成 0 次 · 正確 0 · 誤觸 0 · 漏觸 0")
        self.status_var = tk.StringVar(value="選擇 Pilot 或正式實驗。正式實驗會依提示逐次記錄實際相機觸發結果。")
        self.pilot_summary_var = tk.StringVar(value="Pilot 樣本數：0")
        self.timeout_value = tk.IntVar(value=8)
        self.low_var = tk.StringVar(value="")
        self.medium_var = tk.StringVar(value="")
        self.high_var = tk.StringVar(value="")
        self._build_ui()
        self.app.add_trigger_observer(self._on_trigger)
        self.app.add_snapshot_observer(self._on_snapshot)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh_state()

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self.window, padding=16)
        root_frame.pack(fill="both", expand=True)

        ttk.Label(root_frame, text="HW4 Experiment Runner", font=("Arial", 19, "bold")).pack(anchor="w")
        ttk.Label(root_frame, text="實驗條件與觸發結果由目前的攝影機辨識輸入；每完成一筆便立即寫入 CSV。", wraplength=900).pack(anchor="w", pady=(4, 12))

        selection_row = ttk.Frame(root_frame)
        selection_row.pack(fill="x")
        ttk.Label(selection_row, text="實驗流程").pack(side="left")
        self.selection_box = ttk.Combobox(selection_row, textvariable=self.selection_var, values=[label for label, _code in self.EXPERIMENT_CHOICES], state="readonly", width=51)
        self.selection_box.pack(side="left", padx=(10, 12))
        self.selection_box.bind("<<ComboboxSelected>>", self._on_selection_change)
        self.begin_button = ttk.Button(selection_row, text="開始流程", command=self.start_selected)
        self.begin_button.pack(side="left")
        ttk.Label(selection_row, text="單次試驗逾時").pack(side="left", padx=(18, 6))
        ttk.Spinbox(selection_row, from_=3, to=30, width=5, textvariable=self.timeout_value).pack(side="left")
        ttk.Label(selection_row, text="秒").pack(side="left", padx=(4, 0))

        instruction_box = ttk.LabelFrame(root_frame, text="操作提示", padding=10)
        instruction_box.pack(fill="x", pady=(12, 10))
        ttk.Label(instruction_box, textvariable=self.instruction_var, wraplength=870, justify="left").pack(anchor="w")

        threshold_box = ttk.LabelFrame(root_frame, text="Experiment 2 門檻設定（motion ratio；請依 Pilot 結果設定）", padding=10)
        threshold_box.pack(fill="x", pady=(0, 12))
        self.threshold_entries = {}
        for column, (label, variable) in enumerate((("Low", self.low_var), ("Medium", self.medium_var), ("High", self.high_var))):
            ttk.Label(threshold_box, text="{} (%)".format(label)).grid(row=0, column=column * 2, sticky="w", padx=(0, 5))
            entry = ttk.Entry(threshold_box, textvariable=variable, width=10)
            entry.grid(row=0, column=column * 2 + 1, sticky="w", padx=(0, 18))
            self.threshold_entries[label] = entry
        self.suggestion_button = ttk.Button(threshold_box, text="以 Pilot 分位數填入建議值", command=self.fill_threshold_suggestions)
        self.suggestion_button.grid(row=0, column=6, sticky="w")
        ttk.Label(threshold_box, textvariable=self.pilot_summary_var).grid(row=1, column=0, columnspan=7, sticky="w", pady=(8, 0))

        trial_box = ttk.LabelFrame(root_frame, text="目前試驗", padding=12)
        trial_box.pack(fill="x", pady=(0, 12))
        ttk.Label(trial_box, textvariable=self.trial_var, font=("Arial", 16, "bold")).pack(anchor="w")
        ttk.Label(trial_box, textvariable=self.condition_var, font=("Arial", 12)).pack(anchor="w", pady=(5, 0))

        controls = ttk.Frame(root_frame)
        controls.pack(fill="x")
        self.trial_button = ttk.Button(controls, text="開始此試驗", command=self.start_trial, state="disabled")
        self.trial_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="停止流程", command=self.stop_session, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        ttk.Button(controls, text="停止 Pilot", command=self.stop_pilot).pack(side="right")
        self.pilot_button = ttk.Button(controls, text="開始 Pilot 收集", command=self.start_pilot)
        self.pilot_button.pack(side="right", padx=(0, 8))

        ttk.Label(root_frame, textvariable=self.progress_var, font=("Arial", 11, "bold")).pack(anchor="w", pady=(14, 5))
        ttk.Label(root_frame, textvariable=self.status_var, wraplength=900, justify="left").pack(anchor="w")
        self.output_var = tk.StringVar(value="")
        ttk.Label(root_frame, textvariable=self.output_var, wraplength=900, foreground="#475569").pack(anchor="w", pady=(7, 0))

    def _on_selection_change(self, _event=None) -> None:
        mode = self.choice_by_label.get(self.selection_var.get(), "pilot")
        if mode == "pilot":
            self.instruction_var.set("Pilot 不計入 75 次正式試驗。請先在正常光線下，以平常操作方式移動並觸發操作區；收集數值後再據此設定三組門檻。")
        elif mode == "experiment1":
            self.instruction_var.set("固定目前門檻與正常光線。每次依提示操作一個目標區；命令觸發或逾時後會自動記錄並前進。共 30 次。")
        elif mode == "experiment2":
            self.instruction_var.set("固定正常光線，依序使用 Pilot 推導的 Low、Medium、High 門檻。每個代表指令各測三次，共 27 次。開始前須填入由低至高的三個 motion ratio (%)。")
        else:
            self.instruction_var.set("依提示分別在正常與昏暗光線操作 Previous、Next、Zoom In，各三次，共 18 次。光線變更後先重設背景模型、等待穩定，再開始該試驗。")
        self.refresh_state()

    def start_selected(self) -> None:
        if self.pilot_active:
            self.stop_pilot()
        experiment_id = self.choice_by_label.get(self.selection_var.get(), "pilot")
        if experiment_id == "pilot":
            self.start_pilot()
            return
        if self.active_experiment_id:
            messagebox.showinfo("流程進行中", "請先完成或停止目前的實驗流程。", parent=self.window)
            return

        baseline = self.app.detector.threshold
        levels = None
        if experiment_id == "experiment2":
            try:
                levels = {"Low": float(self.low_var.get()) / 100.0, "Medium": float(self.medium_var.get()) / 100.0, "High": float(self.high_var.get()) / 100.0}
            except ValueError:
                messagebox.showwarning("需要設定門檻", "請先輸入 Low、Medium、High 三組百分比門檻。", parent=self.window)
                return
            if not all(0.0 < value < 1.0 for value in levels.values()) or not (levels["Low"] < levels["Medium"] < levels["High"]):
                messagebox.showwarning("門檻設定無效", "三組門檻必須介於 0% 與 100%，且 Low < Medium < High。", parent=self.window)
                return

        try:
            self.trials = build_trial_schedule(experiment_id, baseline, levels)
        except ValueError as error:
            messagebox.showwarning("無法開始", str(error), parent=self.window)
            return

        self.active_experiment_id = experiment_id
        self.active_experiment_name = self.trials[0].experiment_name
        self.session_baseline_threshold = baseline
        self.threshold_levels = levels or {}
        self.session_started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self.completed_count = 0
        self.session_total = len(self.trials)
        self.correct_count = 0
        self.false_count = 0
        self.missed_count = 0
        output_path = self.recorder.start_experiment(experiment_id)
        self.output_var.set("記錄檔：{}".format(output_path))
        self.app.set_experiment_threshold_lock(True)
        self.trial_var.set("準備開始：{} 次試驗".format(len(self.trials)))
        self.condition_var.set("正式實驗開始後，依序按「開始此試驗」。")
        self.status_var.set("排程已建立；未開始的動作不會記入試驗資料。")
        self._update_progress()
        self.refresh_state()

    def start_trial(self) -> None:
        if not self.active_experiment_id or self.active_trial is not None:
            return
        if not self.trials:
            self._finish_session()
            return

        self.active_trial = self.trials.pop(0)
        self.app.apply_experiment_threshold(self.active_trial.threshold_value)
        self.max_target_motion = 0.0
        self.trial_started_at = time.monotonic()
        self.trial_started_label = datetime.now().astimezone().isoformat(timespec="seconds")
        lighting_text = self.active_trial.lighting
        if self.active_trial.experiment_id == "experiment2":
            condition = "門檻 {} = {:.2f}%".format(self.active_trial.threshold_level, self.active_trial.threshold_value * 100)
        else:
            condition = "固定門檻 {:.2f}%".format(self.active_trial.threshold_value * 100)
        self.trial_var.set("{} / {}  |  目標：{} ({})".format(self.active_trial.trial_id, self.session_total, self.active_trial.target_zone, COMMAND_LABELS[self.active_trial.target_command]))
        self.condition_var.set("條件：{}  |  {}  |  第 {} 次重複".format(lighting_text, condition, self.active_trial.repetition))
        self.status_var.set("請將動作放入目標區 {}。逾時 {} 秒會記為 Missed Trigger。".format(self.active_trial.target_zone, self.timeout_value.get()))
        if self.active_trial.lighting not in self.saved_lighting_evidence:
            self.saved_lighting_evidence.add(self.active_trial.lighting)
            evidence_name = "lighting-{}".format(self.active_trial.lighting.lower().replace(" ", "-"))
            evidence_title = "Lighting condition: {}".format(self.active_trial.lighting)
            self.app.root.after(120, lambda label=evidence_name, title=evidence_title: self.app.capture_evidence(label, title))
        self._update_progress()
        self.refresh_state()
        timeout_seconds = max(3, int(self.timeout_value.get()))
        self.timeout_after_id = self.window.after(timeout_seconds * 1000, self._timeout_trial)

    def _on_snapshot(self, snapshot) -> None:
        if self.active_trial is None:
            return
        self.max_target_motion = max(self.max_target_motion, snapshot.motion_ratios.get(self.active_trial.target_zone, 0.0))

    def _on_trigger(self, zone: str, ratio: float, trigger_time: float) -> None:
        if self.active_trial is not None:
            correct = zone == self.active_trial.target_zone
            latency_ms = (trigger_time - self.trial_started_at) * 1000.0
            self._complete_trial(zone, ratio, latency_ms, correct, false_trigger=not correct, missed_trigger=False)
            return
        if self.pilot_active:
            self.pilot_values.append(ratio)
            self.recorder.record_pilot(zone, ratio, self.app.detector.threshold)
            self.pilot_summary_var.set("Pilot 樣本數：{}  |  最近 motion ratio：{:.2f}%".format(len(self.pilot_values), ratio * 100))
            self.status_var.set("已記錄 Pilot：{} / {}，motion ratio {:.2f}%。繼續收集正常操作樣本。".format(zone, COMMAND_LABELS[COMMANDS[zone]], ratio * 100))

    def _timeout_trial(self) -> None:
        self.timeout_after_id = None
        if self.active_trial is not None:
            self._complete_trial(None, self.max_target_motion, None, False, false_trigger=False, missed_trigger=True)

    def _complete_trial(self, triggered_zone: Optional[str], motion_ratio: float, trigger_time_ms: Optional[float], correct: bool, false_trigger: bool, missed_trigger: bool) -> None:
        trial = self.active_trial
        if trial is None:
            return
        if self.timeout_after_id:
            self.window.after_cancel(self.timeout_after_id)
            self.timeout_after_id = None
        row = {
            "trial_id": trial.trial_id,
            "experiment": trial.experiment_name,
            "condition": trial.lighting if trial.experiment_id != "experiment2" else trial.threshold_level,
            "lighting": trial.lighting,
            "threshold_level": trial.threshold_level,
            "threshold_value": "{:.6f}".format(trial.threshold_value),
            "target_zone": trial.target_zone,
            "target_command": COMMAND_LABELS[trial.target_command],
            "triggered_zone": triggered_zone or "",
            "triggered_command": COMMAND_LABELS[COMMANDS[triggered_zone]] if triggered_zone else "",
            "correct": str(bool(correct)).lower(),
            "motion_ratio": "{:.6f}".format(motion_ratio),
            "trigger_time_ms": "{:.1f}".format(trigger_time_ms) if trigger_time_ms is not None else "",
            "false_trigger": str(bool(false_trigger)).lower(),
            "missed_trigger": str(bool(missed_trigger)).lower(),
            "repetition": trial.repetition,
            "notes": "",
            "started_at": self.trial_started_label,
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        self.recorder.record_trial(row)
        if false_trigger or missed_trigger:
            issue = "false-trigger" if false_trigger else "missed-trigger"
            self.app.root.after(120, lambda label="{}-{}".format(issue, trial.trial_id), title="{}: {}".format(issue.replace("-", " "), trial.trial_id): self.app.capture_evidence(label, title))
        self.completed_count += 1
        if correct:
            self.correct_count += 1
        if false_trigger:
            self.false_count += 1
        if missed_trigger:
            self.missed_count += 1
        self.active_trial = None
        self._update_progress()

        if missed_trigger:
            outcome = "漏觸：未在時間內觸發目標區。"
        elif false_trigger:
            outcome = "誤觸：目標為 {}，實際觸發 {}。".format(trial.target_zone, triggered_zone)
        else:
            outcome = "正確觸發 {}；延遲 {:.0f} ms。".format(triggered_zone, trigger_time_ms)
        self.status_var.set("{} 已保存。{}".format(trial.trial_id, outcome))
        if not self.trials:
            self._finish_session()
        else:
            self.trial_var.set("下一個：{}  |  {} ({})".format(self.trials[0].trial_id, self.trials[0].target_zone, COMMAND_LABELS[self.trials[0].target_command]))
            self.condition_var.set("條件：{}  |  {}".format(self.trials[0].lighting, self.trials[0].threshold_level))
            self.refresh_state()

    def _update_progress(self) -> None:
        false_label = "誤觸 {}".format(self.false_count)
        missed_label = "漏觸 {}".format(self.missed_count)
        self.progress_var.set("已完成 {} 次  |  正確 {}  |  {}  |  {}".format(self.completed_count, self.correct_count, false_label, missed_label))

    def _finish_session(self) -> None:
        if self.timeout_after_id:
            self.window.after_cancel(self.timeout_after_id)
            self.timeout_after_id = None
        experiment_name = self.active_experiment_name
        expected_total = self.session_total
        self.active_experiment_id = None
        self.active_experiment_name = ""
        self.trials = []
        self.active_trial = None
        self.app.apply_experiment_threshold(self.session_baseline_threshold, unlock=True)
        rate = (100.0 * self.correct_count / self.completed_count) if self.completed_count else 0.0
        self.trial_var.set("{} 流程完成".format(experiment_name))
        self.condition_var.set("完成 {} 次中的 {} 次。成功率 {:.1f}%。".format(expected_total, self.completed_count, rate))
        self.status_var.set("所有已完成試驗均已寫入 CSV。結果需依實際試驗解讀，不會自動填補未完成項目。")
        self.refresh_state()

    def stop_session(self) -> None:
        if not self.active_experiment_id:
            return
        if self.timeout_after_id:
            self.window.after_cancel(self.timeout_after_id)
            self.timeout_after_id = None
        self.active_trial = None
        self.trials = []
        self.active_experiment_id = None
        self.app.apply_experiment_threshold(self.session_baseline_threshold, unlock=True)
        self.status_var.set("流程已停止；已完成試驗已保存在 CSV，未開始的試驗未記錄。")
        self.trial_var.set("流程已停止")
        self.refresh_state()

    def start_pilot(self) -> None:
        if self.active_experiment_id:
            messagebox.showinfo("正式實驗進行中", "請先完成或停止正式實驗，再啟動 Pilot。", parent=self.window)
            return
        self.pilot_active = True
        self.pilot_values = []
        self.pilot_summary_var.set("Pilot 樣本數：0  |  資料會附加至 {}".format(self.recorder.pilot_path.name))
        self.status_var.set("Pilot 收集中。請在正常光線下做自然操作；每次相機觸發都會記錄 motion ratio。")
        self.refresh_state()

    def stop_pilot(self) -> None:
        if not self.pilot_active:
            return
        self.pilot_active = False
        self.status_var.set("Pilot 收集已停止。共收集 {} 筆；可按分位數按鈕產生 Low / Medium / High 建議值。".format(len(self.pilot_values)))
        self.refresh_state()

    @staticmethod
    def _quantile(values: Sequence[float], fraction: float) -> float:
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        position = fraction * (len(ordered) - 1)
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    def fill_threshold_suggestions(self) -> None:
        try:
            with self.recorder.pilot_path.open("r", encoding="utf-8-sig", newline="") as stream:
                values = [float(row["motion_ratio"]) for row in csv.DictReader(stream) if row.get("motion_ratio")]
        except (OSError, ValueError, KeyError):
            values = list(self.pilot_values)
        if len(values) < 3:
            messagebox.showinfo("Pilot 樣本不足", "至少收集 3 筆有效 Pilot motion ratio，才顯示分位數建議。", parent=self.window)
            return
        suggestions = (
            self._quantile(values, 0.25),
            self._quantile(values, 0.50),
            self._quantile(values, 0.75),
        )
        self.low_var.set("{:.2f}".format(suggestions[0] * 100))
        self.medium_var.set("{:.2f}".format(suggestions[1] * 100))
        self.high_var.set("{:.2f}".format(suggestions[2] * 100))
        self.status_var.set("已用 {} 筆 Pilot 樣本的第 25、50、75 百分位填入建議門檻；請檢視後再開始 Experiment 2。".format(len(values)))

    def refresh_state(self) -> None:
        active = self.active_experiment_id is not None
        pilot = self.pilot_active
        self.selection_box.configure(state="disabled" if active or pilot else "readonly")
        self.begin_button.configure(state="disabled" if active else "normal")
        self.trial_button.configure(state="normal" if active and self.active_trial is None and self.trials else "disabled")
        self.stop_button.configure(state="normal" if active else "disabled")
        self.pilot_button.configure(state="disabled" if active or pilot else "normal")
        for entry in self.threshold_entries.values():
            entry.configure(state="disabled" if active else "normal")

    def close(self) -> None:
        if self.active_experiment_id:
            self.stop_session()
        self.stop_pilot()
        self.app.remove_trigger_observer(self._on_trigger)
        self.app.remove_snapshot_observer(self._on_snapshot)
        self.app.experiment_window = None
        self.window.destroy()
