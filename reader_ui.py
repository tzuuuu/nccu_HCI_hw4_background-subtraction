"""Touchless Document Reader canvas and command behavior."""

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import tkinter as tk
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageTk

from document_pages import ensure_document_pages


COMMANDS = {
    "Z1": "previous",
    "Z2": "next",
    "Z3": "zoom_in",
    "Z4": "zoom_out",
    "Z5": "menu",
    "Z6": "settings",
}
COMMAND_LABELS = {
    "previous": "Previous Page",
    "next": "Next Page",
    "zoom_in": "Zoom In",
    "zoom_out": "Zoom Out",
    "menu": "Menu",
    "settings": "Settings",
}


class DocumentReaderUI:
    """Render the shared six-zone reader and expose command actions."""

    def __init__(self, root: tk.Tk, on_state_change: Optional[Callable[[], None]] = None) -> None:
        self.root = root
        self.on_state_change = on_state_change
        self.page_index = 0
        self.zoom = 100
        self.theme = "Light"
        self.last_command = "Ready"
        self.camera_status = "Camera starting..."
        self.menu_state: Optional[str] = None
        self.motion_ratios: Dict[str, float] = {"Z1": 0.0, "Z2": 0.0, "Z3": 0.0, "Z4": 0.0, "Z5": 0.0, "Z6": 0.0}
        self.active_zone: Optional[str] = None
        self.triggered_zone: Optional[str] = None
        self.threshold = 0.025
        self._last_trigger_time = 0.0
        self._render_after_id: Optional[str] = None

        page_paths = ensure_document_pages(Path(__file__).parent / "assets" / "pages")
        self.pages = [Image.open(path).convert("RGB") for path in page_paths]
        self.canvas = tk.Canvas(root, highlightthickness=0, background="#e8edf3")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._schedule_render)
        self.canvas.bind("<Button-1>", self._handle_click)
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._last_rendered_image: Optional[Image.Image] = None
        self._menu_hitboxes = []
        self._schedule_render()

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def current_page(self) -> int:
        return self.page_index + 1

    def set_camera_status(self, text: str) -> None:
        self.camera_status = text
        self._schedule_render()

    def set_threshold(self, threshold: float) -> None:
        self.threshold = threshold
        self._schedule_render()

    def set_motion_feedback(self, ratios: Dict[str, float], active_zone: Optional[str], triggered_zone: Optional[str]) -> None:
        self.motion_ratios = dict(ratios)
        self.active_zone = active_zone
        self.triggered_zone = triggered_zone
        self._schedule_render()

    def save_screenshot(self, directory: Optional[Path] = None) -> Path:
        output_dir = directory or (Path(__file__).parent / "screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "reader-{}.png".format(datetime.now().strftime("%Y%m%d-%H%M%S"))
        if self._last_rendered_image is None:
            self._render()
        self._last_rendered_image.save(output_path)
        return output_path

    def execute_command(self, command: str, source: str = "Camera") -> bool:
        """Apply one of the six commands; return whether visible state changed."""
        changed = True
        if command == "previous":
            new_index = max(0, self.page_index - 1)
            changed = new_index != self.page_index
            self.page_index = new_index
        elif command == "next":
            new_index = min(self.page_count - 1, self.page_index + 1)
            changed = new_index != self.page_index
            self.page_index = new_index
        elif command == "zoom_in":
            new_zoom = min(200, self.zoom + 10)
            changed = new_zoom != self.zoom
            self.zoom = new_zoom
        elif command == "zoom_out":
            new_zoom = max(50, self.zoom - 10)
            changed = new_zoom != self.zoom
            self.zoom = new_zoom
        elif command == "menu":
            self.menu_state = "menu"
        elif command == "settings":
            self.menu_state = "settings"
        else:
            return False

        label = COMMAND_LABELS[command]
        if not changed and command in ("previous", "next", "zoom_in", "zoom_out"):
            label += " (limit)"
        self.last_command = "{}: {}".format(source, label)
        self._schedule_render()
        if self.on_state_change:
            self.on_state_change()
        return changed

    def _schedule_render(self, _event=None) -> None:
        if self._render_after_id is not None:
            self.root.after_cancel(self._render_after_id)
        self._render_after_id = self.root.after(35, self._render)

    def _font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        )
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                pass
        return ImageFont.load_default()

    def _render(self) -> None:
        self._render_after_id = None
        width = max(640, self.canvas.winfo_width())
        height = max(480, self.canvas.winfo_height())
        reading_height = int(height * 0.78)
        dark = self.theme == "Dark"
        background = "#101827" if dark else "#edf1f6"
        image = Image.new("RGB", (width, height), background)
        draw = ImageDraw.Draw(image, "RGBA")

        # Center the document page inside the 78% reading area. Higher zooms crop
        # at the reading viewport edges while preserving the image page itself.
        page = self.pages[self.page_index]
        base_scale = min((width * 0.55) / page.width, (reading_height * 0.93) / page.height)
        scale = base_scale * self.zoom / 100.0
        page_width = max(1, int(page.width * scale))
        page_height = max(1, int(page.height * scale))
        display_page = page.resize((page_width, page_height), Image.Resampling.LANCZOS)
        page_x = (width - page_width) // 2
        page_y = max(0, (reading_height - page_height) // 2)
        if self.zoom > 100:
            page_y = max(0, (reading_height - int(reading_height * 0.8)) // 2)
        image.paste(display_page, (page_x, page_y))
        draw = ImageDraw.Draw(image, "RGBA")

        zone_rects = self._zone_rectangles(width, height)
        for zone, rect in zone_rects.items():
            triggered = self.triggered_zone == zone
            active = self.active_zone == zone
            fill = (37, 99, 235, 72 if triggered else 42 if active else 20)
            outline = (37, 99, 235, 220 if triggered else 120 if active else 65)
            draw.rectangle(rect, fill=fill, outline=outline, width=3 if triggered else 2)

        label_font = self._font(max(16, int(width * 0.017)), True)
        small_font = self._font(max(12, int(width * 0.011)))
        for zone, rect in zone_rects.items():
            x1, y1, x2, y2 = rect
            label = COMMAND_LABELS[COMMANDS[zone]]
            value = self.motion_ratios.get(zone, 0.0)
            ratio_text = "{:.1f}%".format(value * 100)
            if zone in ("Z1", "Z2"):
                center_x = (x1 + x2) // 2
                center_y = y1 + int((y2 - y1) * 0.68)
                label_box = draw.textbbox((0, 0), label, font=label_font)
                label_width = label_box[2] - label_box[0]
                draw.text((center_x - label_width / 2, center_y), label, font=label_font, fill=(31, 41, 55, 220))
                detail = "{}  |  Motion {}".format(zone, ratio_text)
                detail_box = draw.textbbox((0, 0), detail, font=small_font)
                draw.text((center_x - (detail_box[2] - detail_box[0]) / 2, center_y + 29), detail, font=small_font, fill=(71, 85, 105, 220))
            else:
                draw.text((x1 + 16, y1 + 15), zone, font=small_font, fill=(71, 85, 105, 220))
                label_box = draw.textbbox((0, 0), label, font=small_font)
                label_width = label_box[2] - label_box[0]
                draw.text(((x1 + x2 - label_width) / 2, y1 + 42), label, font=small_font, fill=(31, 41, 55, 230))
                ratio_box = draw.textbbox((0, 0), ratio_text, font=small_font)
                draw.text(((x1 + x2 - (ratio_box[2] - ratio_box[0])) / 2, y1 + 64), ratio_text, font=small_font, fill=(71, 85, 105, 210))

        # Header badges match the common specification's always-visible feedback.
        header_h = max(48, int(height * 0.075))
        draw.rounded_rectangle((width - 400, 12, width - 16, header_h), radius=14, fill=(255, 255, 255, 225) if not dark else (15, 23, 42, 230))
        badge_font = self._font(max(13, int(width * 0.012)), True)
        badge_text = "Current Page: {} / {}    Zoom: {}%".format(self.current_page, self.page_count, self.zoom)
        draw.text((width - 382, 24), badge_text, font=badge_font, fill="#243044" if not dark else "#e2e8f0")

        toolbar_y = reading_height
        toolbar_color = (255, 255, 255, 235) if not dark else (15, 23, 42, 245)
        draw.rectangle((0, toolbar_y, width, height), fill=toolbar_color)
        draw.line((0, toolbar_y, width, toolbar_y), fill=(37, 99, 235, 150), width=3)
        toolbar_labels = ("Zoom In  +", "Zoom Out  -", "Menu", "Settings")
        toolbar_font = self._font(max(15, int(width * 0.016)), True)
        for index, label in enumerate(toolbar_labels):
            x1 = int(index * width / 4)
            x2 = int((index + 1) * width / 4)
            if index:
                draw.line((x1, toolbar_y + 18, x1, height - 18), fill=(148, 163, 184, 120), width=2)
            box = draw.textbbox((0, 0), label, font=toolbar_font)
            text_width, text_height = box[2] - box[0], box[3] - box[1]
            draw.text(((x1 + x2 - text_width) / 2, toolbar_y + (height - toolbar_y - text_height) / 2), label, font=toolbar_font, fill="#1e293b" if not dark else "#e2e8f0")

        footer_y = max(toolbar_y + 2, height - 27)
        footer_font = self._font(max(10, int(width * 0.009)))
        footer = "Last Command: {}     |     {}     |     Threshold: {:.1f}%".format(self.last_command, self.camera_status, self.threshold * 100)
        draw.text((16, footer_y), footer, font=footer_font, fill="#475569" if not dark else "#cbd5e1")

        if self.menu_state:
            self._draw_popup(image, self.menu_state)

        self._last_rendered_image = image.copy()
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")

    def _zone_rectangles(self, width: int, height: int) -> Dict[str, Tuple[int, int, int, int]]:
        reading_height = int(height * 0.78)
        toolbar_height = height - reading_height
        rectangles = {
            "Z1": (0, 0, width // 2, reading_height),
            "Z2": (width // 2, 0, width, reading_height),
        }
        names = ("Z3", "Z4", "Z5", "Z6")
        for index, zone in enumerate(names):
            x1 = int(index * width / 4)
            x2 = int((index + 1) * width / 4)
            rectangles[zone] = (x1, reading_height, x2, reading_height + toolbar_height)
        return rectangles

    def _draw_popup(self, image: Image.Image, state: str) -> None:
        width, height = image.size
        draw = ImageDraw.Draw(image, "RGBA")
        panel_width = min(520, width - 80)
        panel_height = min(430, height - 120)
        x1 = (width - panel_width) // 2
        y1 = (int(height * 0.78) - panel_height) // 2
        x2, y2 = x1 + panel_width, y1 + panel_height
        draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=(255, 255, 255, 248), outline=(37, 99, 235, 210), width=3)
        title = "Menu" if state == "menu" else "Settings"
        draw.text((x1 + 30, y1 + 24), title, font=self._font(32, True), fill="#1e293b")
        self._menu_hitboxes = []
        items = (
            (("Current Page: {} / {}".format(self.current_page, self.page_count), None),
             ("Go to First Page", "first"),
             ("Go to Last Page", "last"),
             ("Close", "close"))
            if state == "menu" else
            (("Theme: {}".format(self.theme), "theme"),
             ("Reset Zoom", "reset_zoom"),
             ("Close", "close"))
        )
        item_y = y1 + 88
        item_height = 58
        for label, action in items:
            rect = (x1 + 24, item_y, x2 - 24, item_y + item_height - 8)
            draw.rounded_rectangle(rect, radius=12, fill=(239, 244, 250, 255), outline=(203, 213, 225, 255), width=1)
            draw.text((rect[0] + 18, rect[1] + 13), label, font=self._font(19, action is not None), fill="#334155")
            self._menu_hitboxes.append((rect, action))
            item_y += item_height

    def _handle_click(self, event: tk.Event) -> None:
        for rect, action in self._menu_hitboxes:
            x1, y1, x2, y2 = rect
            if x1 <= event.x <= x2 and y1 <= event.y <= y2 and action:
                self._apply_popup_action(action)
                return

    def _apply_popup_action(self, action: str) -> None:
        if action == "first":
            self.page_index = 0
            self.last_command = "Menu: Go to First Page"
        elif action == "last":
            self.page_index = self.page_count - 1
            self.last_command = "Menu: Go to Last Page"
        elif action == "theme":
            self.theme = "Dark" if self.theme == "Light" else "Light"
            self.last_command = "Settings: Theme {}".format(self.theme)
        elif action == "reset_zoom":
            self.zoom = 100
            self.last_command = "Settings: Reset Zoom"
        self.menu_state = None
        self._schedule_render()
        if self.on_state_change:
            self.on_state_change()
