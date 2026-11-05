"""Run the HW4 vision-based touchless document reader."""

import argparse
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, List, Optional

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageTk

from background_subtraction import CameraMotionDetector, MotionSnapshot, ZONE_ORDER, zone_rectangles
from reader_ui import COMMANDS, COMMAND_LABELS, DocumentReaderUI


APP_DIR = Path(__file__).resolve().parent


class TouchlessReaderApp:
    def __init__(self, root: tk.Tk, camera_index: int = 0) -> None:
        self.root = root
        self.root.title("Touchless Document Reader — HW4")
        self.root.geometry("1280x820")
        self.root.minsize(900, 640)
        self.detector = CameraMotionDetector(camera_index=camera_index)
        self.reader = DocumentReaderUI(root, on_state_change=self._refresh_experiment_state)
        self.diagnostics: Optional[tk.Toplevel] = None
        self.camera_photo: Optional[ImageTk.PhotoImage] = None
        self.mask_photo: Optional[ImageTk.PhotoImage] = None
        self.camera_image_label: Optional[ttk.Label] = None
        self.mask_image_label: Optional[ttk.Label] = None
        self.camera_status_var: Optional[tk.StringVar] = None
        self.last_snapshot: Optional[MotionSnapshot] = None
        self.last_frame_bgr = None
        self.last_mask = None
        self.trigger_observers: List[Callable[[str, float, float], None]] = []
        self.experiment_window = None
        self._build_menu()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.open_diagnostics()
        self.root.after(25, self._update_camera)

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Save Reader Screenshot", command=self._save_reader_screenshot)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.close)
        menu_bar.add_cascade(label="File", menu=file_menu)

        camera_menu = tk.Menu(menu_bar, tearoff=False)
        camera_menu.add_command(label="Camera Diagnostics", command=self.open_diagnostics)
        camera_menu.add_command(label="Retry Camera", command=self.retry_camera)
        camera_menu.add_command(label="Reset Background Model", command=self.reset_background)
        menu_bar.add_cascade(label="Camera", menu=camera_menu)

        reader_menu = tk.Menu(menu_bar, tearoff=False)
        reader_menu.add_command(label="Menu", command=lambda: self.reader.execute_command("menu", "Toolbar"))
        reader_menu.add_command(label="Settings", command=lambda: self.reader.execute_command("settings", "Toolbar"))
        menu_bar.add_cascade(label="Reader", menu=reader_menu)
        self.root.config(menu=menu_bar)

    def open_diagnostics(self) -> None:
        if self.diagnostics is not None and self.diagnostics.winfo_exists():
            self.diagnostics.deiconify()
            self.diagnostics.lift()
            return

        window = tk.Toplevel(self.root)
        window.title("Camera / Foreground Mask — HW4 Diagnostics")
        window.geometry("1120x700")
        window.minsize(900, 620)
        self.diagnostics = window
        container = ttk.Frame(window, padding=14)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="Background Subtraction Diagnostics", font=("Arial", 18, "bold"))
        title.pack(anchor="w")
        intro = ttk.Label(container, text="Camera preview and MOG2 foreground mask. Blue region outlines match the six reader zones.")
        intro.pack(anchor="w", pady=(4, 12))

        preview_row = ttk.Frame(container)
        preview_row.pack(fill="both", expand=True)
        camera_col = ttk.LabelFrame(preview_row, text="Mirrored Camera Input")
        mask_col = ttk.LabelFrame(preview_row, text="Foreground Mask (white = changed pixels)")
        camera_col.pack(side="left", fill="both", expand=True, padx=(0, 7))
        mask_col.pack(side="left", fill="both", expand=True, padx=(7, 0))
        self.camera_image_label = ttk.Label(camera_col, text="Waiting for camera…", anchor="center")
        self.mask_image_label = ttk.Label(mask_col, text="Waiting for camera…", anchor="center")
        self.camera_image_label.pack(fill="both", expand=True, padx=8, pady=8)
        self.mask_image_label.pack(fill="both", expand=True, padx=8, pady=8)

        self.camera_status_var = tk.StringVar(value=self._camera_open_status())
        status = ttk.Label(container, textvariable=self.camera_status_var, font=("Arial", 11, "bold"))
        status.pack(anchor="w", pady=(8, 6))

        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=(2, 0))
        ttk.Label(controls, text="Threshold (% motion ratio)").grid(row=0, column=0, sticky="w")
        self.threshold_value = tk.DoubleVar(value=self.detector.threshold * 100)
        ttk.Scale(controls, from_=0.5, to=15.0, variable=self.threshold_value, command=self._on_threshold_change).grid(row=1, column=0, sticky="ew", padx=(0, 18))
        self.threshold_label_var = tk.StringVar(value="{:.1f}%".format(self.threshold_value.get()))
        ttk.Label(controls, textvariable=self.threshold_label_var, width=7).grid(row=1, column=1, sticky="w")

        ttk.Label(controls, text="Consecutive frames").grid(row=0, column=2, sticky="w", padx=(18, 0))
        self.consecutive_value = tk.IntVar(value=3)
        consecutive_box = ttk.Spinbox(controls, from_=1, to=12, width=5, textvariable=self.consecutive_value, command=self._on_confirmation_change)
        consecutive_box.grid(row=1, column=2, sticky="w", padx=(18, 6))
        consecutive_box.bind("<FocusOut>", self._on_confirmation_change)

        ttk.Label(controls, text="Cooldown (seconds)").grid(row=0, column=3, sticky="w", padx=(18, 0))
        self.cooldown_value = tk.DoubleVar(value=1.0)
        ttk.Spinbox(controls, from_=0.0, to=5.0, increment=0.1, width=6, textvariable=self.cooldown_value, command=self._on_cooldown_change).grid(row=1, column=3, sticky="w", padx=(18, 6))

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Retry Camera", command=self.retry_camera).pack(side="left")
        ttk.Button(actions, text="Reset Background Model", command=self.reset_background).pack(side="left", padx=8)
        ttk.Button(actions, text="Save Mask Screenshot", command=self._save_mask_screenshot).pack(side="left")
        ttk.Button(actions, text="Save Reader Screenshot", command=self._save_reader_screenshot).pack(side="left", padx=8)
        ttk.Button(actions, text="Open Experiment Runner", command=self.open_experiment_runner).pack(side="right")
        controls.columnconfigure(0, weight=1)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)

    def _camera_open_status(self) -> str:
        if self.detector.is_open:
            return "Camera {} connected · learning background".format(self.detector.camera_index)
        return "Camera unavailable · use Retry Camera and allow camera access"

    def _on_threshold_change(self, _value=None) -> None:
        threshold = max(0.001, min(0.95, self.threshold_value.get() / 100.0))
        self.detector.configure(threshold=threshold)
        self.reader.set_threshold(threshold)
        self.threshold_label_var.set("{:.1f}%".format(threshold * 100))
        self._refresh_experiment_state()

    def _on_confirmation_change(self, _event=None) -> None:
        try:
            self.detector.configure(consecutive_frames=max(1, int(self.consecutive_value.get())))
        except (ValueError, tk.TclError):
            return

    def _on_cooldown_change(self) -> None:
        try:
            self.detector.configure(cooldown_seconds=max(0.0, float(self.cooldown_value.get())))
        except (ValueError, tk.TclError):
            return

    def retry_camera(self) -> None:
        opened = self.detector.open()
        self.detector.reset_background()
        status = "Camera {} connected · learning background".format(self.detector.camera_index) if opened else "Camera unavailable · check permission or camera index"
        self.reader.set_camera_status(status)
        if self.camera_status_var is not None:
            self.camera_status_var.set(status)

    def reset_background(self) -> None:
        self.detector.reset_background()
        self.reader.set_camera_status("Learning background…")
        if self.camera_status_var is not None:
            self.camera_status_var.set("Background model reset · keep the scene still while it learns")

    def _update_camera(self) -> None:
        if not self.root.winfo_exists():
            return
        snapshot = self.detector.read(time.monotonic())
        if snapshot is None:
            self.reader.set_camera_status("Camera unavailable" if not self.detector.is_open else "Waiting for camera frame")
            if self.camera_status_var is not None and self.diagnostics is not None and self.diagnostics.winfo_exists():
                self.camera_status_var.set(self._camera_open_status())
        else:
            self.last_snapshot = snapshot
            self.last_frame_bgr = snapshot.frame_bgr.copy()
            self.last_mask = snapshot.foreground_mask.copy()
            self.reader.set_camera_status(snapshot.status)
            self.reader.set_motion_feedback(snapshot.motion_ratios, snapshot.active_zone, snapshot.triggered_zone)
            if snapshot.triggered_zone:
                command = COMMANDS[snapshot.triggered_zone]
                self.reader.execute_command(command)
                trigger_time = time.monotonic()
                for observer in list(self.trigger_observers):
                    observer(snapshot.triggered_zone, snapshot.trigger_ratio, trigger_time)
            if self.camera_status_var is not None and self.diagnostics is not None and self.diagnostics.winfo_exists():
                ratios = "  ".join("{} {:.1f}%".format(zone, snapshot.motion_ratios[zone] * 100) for zone in ZONE_ORDER)
                self.camera_status_var.set("{}  ·  Threshold {:.1f}%  ·  {}".format(snapshot.status, self.detector.threshold * 100, ratios))
            self._render_diagnostics(snapshot)
        self.root.after(25, self._update_camera)

    def _render_diagnostics(self, snapshot: MotionSnapshot) -> None:
        if self.diagnostics is None or not self.diagnostics.winfo_exists():
            return
        frame = snapshot.frame_bgr.copy()
        mask = cv2.cvtColor(snapshot.foreground_mask, cv2.COLOR_GRAY2BGR)
        height, width = frame.shape[:2]
        for zone, rect in zone_rectangles(width, height).items():
            x1, y1, x2, y2 = rect
            active = zone == snapshot.active_zone
            triggered = zone == snapshot.triggered_zone
            color = (0, 0, 255) if triggered else (255, 110, 25) if active else (220, 130, 35)
            thickness = 3 if triggered else 2
            cv2.rectangle(frame, (x1, y1), (x2 - 1, y2 - 1), color, thickness)
            cv2.rectangle(mask, (x1, y1), (x2 - 1, y2 - 1), color, thickness)
            label = "{} {:.1f}%".format(zone, snapshot.motion_ratios[zone] * 100)
            text_y = min(height - 8, y1 + 23)
            cv2.putText(frame, label, (x1 + 8, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2, cv2.LINE_AA)
            cv2.putText(mask, label, (x1 + 8, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2, cv2.LINE_AA)
        self._update_preview_label(self.camera_image_label, frame, "camera")
        self._update_preview_label(self.mask_image_label, mask, "mask")

    def _update_preview_label(self, label: Optional[ttk.Label], frame_bgr, which: str) -> None:
        if label is None or not label.winfo_exists():
            return
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail((500, 365), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        label.configure(image=photo, text="")
        if which == "camera":
            self.camera_photo = photo
        else:
            self.mask_photo = photo

    def _save_reader_screenshot(self) -> None:
        path = self.reader.save_screenshot()
        self.reader.set_camera_status("Saved {}".format(path.name))

    def _save_mask_screenshot(self) -> None:
        if self.last_snapshot is None:
            messagebox.showinfo("No camera frame", "等待攝影機取得畫面後再儲存遮罩截圖。", parent=self.root)
            return
        frame = self.last_snapshot.frame_bgr.copy()
        mask = cv2.cvtColor(self.last_snapshot.foreground_mask, cv2.COLOR_GRAY2BGR)
        height, width = frame.shape[:2]
        for zone, rect in zone_rectangles(width, height).items():
            x1, y1, x2, y2 = rect
            cv2.rectangle(frame, (x1, y1), (x2 - 1, y2 - 1), (220, 130, 35), 2)
            cv2.rectangle(mask, (x1, y1), (x2 - 1, y2 - 1), (220, 130, 35), 2)
            label = "{} {:.1f}%".format(zone, self.last_snapshot.motion_ratios[zone] * 100)
            cv2.putText(mask, label, (x1 + 8, min(height - 8, y1 + 22)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 130, 35), 1, cv2.LINE_AA)
        camera_rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        mask_rgb = Image.fromarray(cv2.cvtColor(mask, cv2.COLOR_BGR2RGB))
        combined = Image.new("RGB", (camera_rgb.width * 2, camera_rgb.height + 48), "white")
        combined.paste(camera_rgb, (0, 48))
        combined.paste(mask_rgb, (camera_rgb.width, 48))
        draw = ImageDraw.Draw(combined)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
        except OSError:
            font = ImageFont.load_default()
        draw.text((14, 12), "Camera Input", font=font, fill="#1e293b")
        draw.text((camera_rgb.width + 14, 12), "Foreground Mask · MOG2", font=font, fill="#1e293b")
        path = APP_DIR / "screenshots" / "foreground-mask.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        combined.save(path)
        self.reader.set_camera_status("Saved {}".format(path.name))

    def add_trigger_observer(self, callback: Callable[[str, float, float], None]) -> None:
        if callback not in self.trigger_observers:
            self.trigger_observers.append(callback)

    def remove_trigger_observer(self, callback: Callable[[str, float, float], None]) -> None:
        if callback in self.trigger_observers:
            self.trigger_observers.remove(callback)

    def open_experiment_runner(self) -> None:
        from experiment_runner import ExperimentRunnerWindow

        if self.experiment_window is not None and self.experiment_window.window.winfo_exists():
            self.experiment_window.window.deiconify()
            self.experiment_window.window.lift()
            return
        self.experiment_window = ExperimentRunnerWindow(self)

    def _refresh_experiment_state(self) -> None:
        if self.experiment_window is not None:
            self.experiment_window.refresh_state()

    def close(self) -> None:
        try:
            self.detector.release()
        finally:
            self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="HW4 touchless document reader")
    parser.add_argument("--camera", type=int, default=0, help="camera device index (default: 0)")
    args = parser.parse_args()
    root = tk.Tk()
    TouchlessReaderApp(root, camera_index=args.camera)
    root.mainloop()


if __name__ == "__main__":
    main()
