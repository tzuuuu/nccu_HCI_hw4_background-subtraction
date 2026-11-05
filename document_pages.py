"""Build the image-based reading pages used by the demo application."""

from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont


PAGE_SIZE = (1050, 1350)
PAGE_CONTENT: Sequence[Tuple[str, Sequence[str]]] = (
    (
        "Designing Touchless Reading Interfaces",
        (
            "A small field guide to vision-based interaction",
            "Reading interfaces are usually designed around a mouse, keyboard, or direct touch. A camera can offer another path: readers can move through a document without touching a shared display or holding a controller.",
            "This guide follows one practical design question: how can a simple camera interaction remain understandable, predictable, and measurable? It uses a document reader as a concrete example and treats the interface and recognition method as one system.",
            "The demo uses six large regions, image-based pages, and visible feedback. Its recognizer observes foreground change only. It does not identify a hand or infer a body pose.",
        ),
    ),
    (
        "Why offer touchless controls?",
        (
            "Touchless interaction can help when a screen is shared, when a reader's hands are occupied, or when direct contact is inconvenient. It can also make a public display easier to explore from a short distance.",
            "A camera interface introduces new demands. The reader must know where to act, whether the camera is ready, and what the system just did. Large regions and immediate feedback reduce the need to remember hidden gestures.",
            "Touchless control is an additional access path rather than a universal replacement for direct input. A useful design keeps ordinary controls available and makes recognition failures easy to notice and recover from.",
        ),
    ),
    (
        "A background subtraction pipeline",
        (
            "Background subtraction compares each camera frame with a model of the scene. Pixels that differ enough from the learned background are marked as foreground. A person can interact by moving an object through one of the visible regions.",
            "The processing path is: capture a frame, update the background model, clean the foreground mask, crop each hot zone, and calculate its changed-pixel ratio. A command is considered only when a zone stays above its threshold for several consecutive frames.",
            "The method reports change, not identity. A waving hand, a moving book, and a sudden exposure shift can all produce foreground pixels. This simple boundary is useful for a controlled experiment because it makes the assumptions explicit.",
        ),
    ),
    (
        "Six large interaction regions",
        (
            "The reading area occupies the upper 78 percent of the interface. Its left half moves to the previous page and its right half moves to the next page. The toolbar occupies the lower 22 percent.",
            "The four toolbar regions control zoom in, zoom out, menu, and settings. Each region is large enough to target without precise pointing. The same proportions are drawn over the camera preview so that users can see where motion will be interpreted.",
            "A consistent layout reduces mode confusion. The same six regions keep their meaning throughout the demo, while the current page, zoom level, and last command remain visible as feedback.",
        ),
    ),
    (
        "Thresholds and motion ratio",
        (
            "Zones can have different pixel areas, so raw changed-pixel counts are difficult to compare. The demo uses a motion ratio: foreground pixels divided by the area of that zone. The result is a value between zero and one.",
            "A low threshold can respond to small movements but may also respond to noise. A high threshold filters small changes but can miss subtle gestures. The useful range depends on camera distance, lighting, background texture, and the size of the movement.",
            "The experiment first records pilot motion ratios under normal lighting. Those observations guide low, medium, and high settings. The settings are chosen from measured operation rather than from a fixed pixel count.",
        ),
    ),
    (
        "Making command triggering reliable",
        (
            "A single foreground frame is not enough evidence for a command. Requiring a zone to exceed its threshold on consecutive frames helps reject brief sensor noise. A cooldown prevents a held movement from issuing commands too quickly.",
            "After a command, the detector waits for the zone to settle below a release level before it can trigger again. This re-arming step makes one continuous movement count as one action, even if it lasts longer than the confirmation window.",
            "Feedback closes the loop: the selected region is highlighted, the last command is named, and page or zoom state updates immediately. When no command is recognized, the reader stays unchanged.",
        ),
    ),
    (
        "A three-part evaluation",
        (
            "The basic accuracy experiment checks all six commands five times each under normal lighting. It records the target and triggered zones, correctness, motion ratio, trigger time, and false triggers.",
            "The threshold experiment compares low, medium, and high settings for previous page, next page, and zoom in. The lighting experiment repeats those representative commands under normal and dim lighting.",
            "Across the three experiments there are 75 planned trials. Success rate, missed triggers, false triggers, motion ratio, and response time help describe both interaction quality and failure patterns.",
        ),
    ),
    (
        "Limits and design implications",
        (
            "Background subtraction is inexpensive and easy to explain, but it is sensitive to changes in the scene. Automatic camera exposure, shadows, moving backgrounds, and a changing light source can affect the mask.",
            "Large zones make targeting easier, yet they can also capture unintended motion. Consecutive-frame confirmation and cooldowns reduce accidental repeats, but they cannot determine whether foreground change was intentional.",
            "The evaluation should report misses and false triggers alongside successful actions. Observed limitations are part of the result: they show when a lightweight vision method works well and what a reader needs to understand its feedback.",
        ),
    ),
)


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_paragraph(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=font) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _render_page(index: int, title: str, paragraphs: Sequence[str], output_path: Path) -> None:
    width, height = PAGE_SIZE
    image = Image.new("RGB", PAGE_SIZE, "#fbfaf7")
    draw = ImageDraw.Draw(image)
    ink = "#243044"
    muted = "#64748b"
    accent = "#2563eb"
    margin = 104
    content_width = width - margin * 2

    draw.rounded_rectangle((margin, 88, margin + 108, 98), radius=5, fill=accent)
    draw.text((margin, 132), "HCI  /  VISION-BASED INTERACTION", font=_load_font(22, True), fill=muted)

    title_font = _load_font(56, True)
    title_lines = _wrap_paragraph(draw, title, title_font, content_width)
    y = 206
    for line in title_lines:
        draw.text((margin, y), line, font=title_font, fill=ink)
        y += 70
    y += 44

    body_font = _load_font(29)
    line_height = 46
    paragraph_gap = 32
    for paragraph in paragraphs:
        for line in _wrap_paragraph(draw, paragraph, body_font, content_width):
            if y + line_height > height - 150:
                break
            draw.text((margin, y), line, font=body_font, fill="#354155")
            y += line_height
        y += paragraph_gap

    draw.line((margin, height - 104, width - margin, height - 104), fill="#d8dee8", width=2)
    draw.text((margin, height - 78), "TOUCHLESS DOCUMENT READER", font=_load_font(17, True), fill=muted)
    page_label = "{:02d} / {:02d}".format(index, len(PAGE_CONTENT))
    label_width = draw.textlength(page_label, font=_load_font(18, True))
    draw.text((width - margin - label_width, height - 80), page_label, font=_load_font(18, True), fill=muted)
    image.save(output_path, format="PNG", optimize=True)


def ensure_document_pages(output_dir: Path = Path("assets/pages")) -> List[Path]:
    """Create the eight demo pages when they are absent and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for index, (title, paragraphs) in enumerate(PAGE_CONTENT, start=1):
        path = output_dir / "page-{:02d}.png".format(index)
        if not path.exists():
            _render_page(index, title, paragraphs, path)
        paths.append(path)
    return paths


if __name__ == "__main__":
    for page_path in ensure_document_pages():
        print(page_path)
