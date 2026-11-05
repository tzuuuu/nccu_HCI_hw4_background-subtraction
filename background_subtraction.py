"""Camera capture and six-zone motion detection using OpenCV MOG2 only."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import cv2
import numpy as np


ZONE_ORDER = ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6")


@dataclass
class MotionSnapshot:
    frame_bgr: np.ndarray
    foreground_mask: np.ndarray
    motion_ratios: Dict[str, float]
    active_zone: Optional[str]
    triggered_zone: Optional[str]
    trigger_ratio: float
    status: str
    frame_number: int


def zone_rectangles(width: int, height: int) -> Dict[str, Tuple[int, int, int, int]]:
    """Return (x1, y1, x2, y2) ROIs matching the frozen 78/22 UI layout."""
    reading_height = int(height * 0.78)
    rectangles = {
        "Z1": (0, 0, width // 2, reading_height),
        "Z2": (width // 2, 0, width, reading_height),
    }
    for index, zone in enumerate(("Z3", "Z4", "Z5", "Z6")):
        x1 = int(index * width / 4)
        x2 = int((index + 1) * width / 4)
        rectangles[zone] = (x1, reading_height, x2, height)
    return rectangles


class CameraMotionDetector:
    """Capture mirrored camera frames and emit confirmed foreground changes."""

    def __init__(
        self,
        camera_index: int = 0,
        frame_size: Tuple[int, int] = (640, 480),
        threshold: float = 0.025,
        consecutive_frames: int = 3,
        cooldown_seconds: float = 1.0,
        warmup_frames: int = 45,
    ) -> None:
        self.camera_index = camera_index
        self.frame_size = frame_size
        self.threshold = threshold
        self.consecutive_frames = consecutive_frames
        self.cooldown_seconds = cooldown_seconds
        self.warmup_frames = warmup_frames
        self.capture: Optional[cv2.VideoCapture] = None
        self.background = self._new_background_model()
        self.frame_number = 0
        self.consecutive_counts = {zone: 0 for zone in ZONE_ORDER}
        self.release_counts = {zone: 0 for zone in ZONE_ORDER}
        self.latched_zones = set()
        self.last_trigger_timestamp = 0.0
        self.open()

    @staticmethod
    def _new_background_model():
        return cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=24,
            detectShadows=True,
        )

    @property
    def is_open(self) -> bool:
        return self.capture is not None and self.capture.isOpened()

    def open(self) -> bool:
        if self.capture is not None:
            self.capture.release()
        self.capture = cv2.VideoCapture(self.camera_index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_size[0])
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_size[1])
        return self.capture.isOpened()

    def reset_background(self) -> None:
        self.background = self._new_background_model()
        self.frame_number = 0
        self.consecutive_counts = {zone: 0 for zone in ZONE_ORDER}
        self.release_counts = {zone: 0 for zone in ZONE_ORDER}
        self.latched_zones.clear()
        self.last_trigger_timestamp = 0.0

    def configure(self, threshold: Optional[float] = None, consecutive_frames: Optional[int] = None, cooldown_seconds: Optional[float] = None) -> None:
        if threshold is not None:
            if not 0.0 < threshold < 1.0:
                raise ValueError("threshold 必須介於 0 與 1 之間")
            self.threshold = threshold
        if consecutive_frames is not None:
            if consecutive_frames < 1:
                raise ValueError("consecutive_frames 必須至少為 1")
            self.consecutive_frames = consecutive_frames
        if cooldown_seconds is not None:
            if cooldown_seconds < 0:
                raise ValueError("cooldown_seconds 不可小於 0")
            self.cooldown_seconds = cooldown_seconds

    def read(self, monotonic_seconds: float) -> Optional[MotionSnapshot]:
        if not self.is_open:
            return None
        ok, captured = self.capture.read()
        if not ok or captured is None:
            return None

        frame = cv2.flip(captured, 1)
        frame = cv2.resize(frame, self.frame_size, interpolation=cv2.INTER_AREA)
        raw_mask = self.background.apply(frame)
        _, mask = cv2.threshold(raw_mask, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8))
        self.frame_number += 1

        height, width = mask.shape[:2]
        rectangles = zone_rectangles(width, height)
        ratios: Dict[str, float] = {}
        for zone in ZONE_ORDER:
            x1, y1, x2, y2 = rectangles[zone]
            roi = mask[y1:y2, x1:x2]
            ratios[zone] = float(np.count_nonzero(roi)) / float(max(1, roi.size))

        if self.frame_number <= self.warmup_frames:
            return MotionSnapshot(frame, mask, ratios, None, None, 0.0, "Learning background…", self.frame_number)

        triggered_zone = None
        trigger_ratio = 0.0
        release_threshold = max(0.004, self.threshold * 0.45)
        candidates = []
        for zone in ZONE_ORDER:
            ratio = ratios[zone]
            if zone in self.latched_zones:
                if ratio <= release_threshold:
                    self.release_counts[zone] += 1
                    if self.release_counts[zone] >= 3:
                        self.latched_zones.remove(zone)
                        self.release_counts[zone] = 0
                else:
                    self.release_counts[zone] = 0
                self.consecutive_counts[zone] = 0
                continue

            if ratio >= self.threshold:
                self.consecutive_counts[zone] += 1
                if self.consecutive_counts[zone] >= self.consecutive_frames:
                    candidates.append(zone)
            else:
                self.consecutive_counts[zone] = 0

        cooldown_done = monotonic_seconds - self.last_trigger_timestamp >= self.cooldown_seconds
        if candidates and cooldown_done:
            triggered_zone = max(candidates, key=lambda zone: ratios[zone])
            trigger_ratio = ratios[triggered_zone]
            self.latched_zones.add(triggered_zone)
            self.consecutive_counts[triggered_zone] = 0
            self.last_trigger_timestamp = monotonic_seconds

        active_zone = max(ratios, key=ratios.get) if max(ratios.values()) >= self.threshold * 0.6 else None
        status = "Ready" if triggered_zone is None else "Triggered {}".format(triggered_zone)
        return MotionSnapshot(frame, mask, ratios, active_zone, triggered_zone, trigger_ratio, status, self.frame_number)

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
