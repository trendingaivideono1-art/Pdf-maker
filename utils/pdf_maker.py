"""
Beautiful PDF Generator
Styled cover page + formatted content
Shows which sources were used (Audio / Board OCR)
"""

import os
import re
import tempfile
import logging
from datetime import datetime
from fpdf import FPDF

logger = logging.getLogger(__name__)

THEMES = {
    "study":   {"primary": (41, 128, 185),  "accent": (39, 174, 96),   "light": (236, 245, 255)},
    "summary": {"primary": (142, 68, 173),  "accent": (230, 126, 34),  "light": (245, 236, 255)},
    "mindmap": {"primary": (22, 160, 133),  "accent": (52, 152, 219),  "light": (225, 250, 245)},
    "qa":      {"primary": (192, 57, 43),   "accent": (41, 128, 185),  "light": (255, 240, 240)},
}

STYLE_LABELS = {
    "study":   "Study Notes",
    "summary": "Summary",
    "mindmap": "Mind Map",
    "qa":      "Q&A Guide",
}


class SmartPDF(FPDF):
    def __init__(self, title: str, style: str, sources: str):
        super().__init__()
        self.doc_title = title
        self.style = style
        self.sources = sources
        self.theme = THEMES.get(style, THEMES["study"])
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(15, 18, 15)

    def header(self):
        r, g, b = self.theme["primary"]
        self.set_fill_color(r, g, b)
        self.rect(0, 0, 210, 7, "F")
        self.set_y(10)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(r, g, b)
        self.cell(0, 5, f"▶  YouTube Smart PDF Bot  •  {STYLE_LABELS.get(self.style, '')}",
                  align="L", ln=True)
        self.set_draw_color(r, g, b)
        self.set_line_width(0.3)
        self.line(15, self.get_y() + 1, 195, self.get_y() + 1)
        self.ln(4)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(160, 160, 160)
        date_str = datetime.now().strftime("%d %b %Y")
        self.cell(0, 5,
                  f"Sources: {self.sources}  •  {date_str}  •  Page {self.page_no()}",
                  align="C")

    def add_cover(self):
        self.add_page()
        r, g, b   = self.theme["primary"]
        ar, ag, ab = self.theme["accent"]

        # Banner
        self.set_fill_color(r, g, b)
        self.rect(0, 0, 210, 90, "F")

        # Source badges on banner
        self.set_y(18)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, self.sources, align="C", ln=True)

        # Title
        self.ln(4)
        self.set_font("Helvetica", "B", 20)
        title = self.doc_title if len(self.doc_title) <= 50 else self.doc_title[:47] + "..."
        self.multi_cell(0, 11, title, align="C")

        # Style pill
        self.set_y(78)
        self.set_fill_color(ar, ag, ab)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 10,
                  f"  📄 {STYLE_LABELS.get(self.style, 'Notes')}  •  Generated {datetime.now().strftime('%d %b %Y')}  ",
                  fill=True, align="C", ln=True)

        # Info box
        self.ln(8)
        lr, lg, lb = self.theme["light"]
        self.set_fill_color(lr, lg, lb)
        self.set_draw_color(r, g, b)
        self.set_line_width(0.5)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 80)
        self.multi_cell(0, 7,
                        "This PDF was generated using:\n"
                        "• AI-powered audio transcript analysis\n"
                        "• Board/screen text via OCR (Computer Vision)\n"
                        "• Claude AI for intelligent note structuring",
                        border=1, fill=True, align="L")
        self.ln(6)


def generate_pdf(notes: str, video_title: str, style: str = "study", sources: str = "") -> str:
    pdf = SmartPDF(video_title, style, sources)
    theme = pdf.theme
    r, g, b    = theme["primary"]
    ar, ag, ab = theme["accent"]
    lr, lg, lb = theme["light"]

    pdf.add_cover()
    pdf.add_page()

    for line in notes.split("\n"):
        raw = line.rstrip()
        stripped = raw.strip()

        if not stripped:
            pdf.ln(2)
            continue

        # H1
        if stripped.startswith("# ") and not stripped.startswith("## "):
            pdf.set_font("Helvetica", "B", 15)
            pdf.set_text_color(r, g, b)
            pdf.multi_cell(0, 9, stripped[2:].strip())
            pdf.set_draw_color(r, g, b)
            pdf.set_line_width(0.5)
            pdf.line(15, pdf.get_y() + 1, 195, pdf.get_y() + 1)
            pdf.ln(5)

        # H2
        elif stripped.startswith("## "):
            pdf.ln(2)
            pdf.set_fill_color(lr, lg, lb)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(r, g, b)
            pdf.multi_cell(0, 8, "  " + stripped[3:].strip(), fill=True)
            pdf.ln(2)

        # H3
        elif stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(ar, ag, ab)
            pdf.multi_cell(0, 7, stripped[4:].strip())
            pdf.ln(1)

        # Arrows (mindmap branches)
        elif stripped.startswith("→") or stripped.startswith("  →"):
            indent = 12 if stripped.startswith("  →") else 6
            txt = stripped.lstrip("→ ").strip()
            txt = re.sub(r"\*\*(.*?)\*\*", r"\1", txt)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(60, 60, 80)
            pdf.set_x(15 + indent)
            pdf.multi_cell(0, 6, f"  ➜  {txt}")

        # Bullets
        elif stripped.startswith(("-", "*", "•")):
            # Detect indentation
            indent = len(raw) - len(raw.lstrip())
            txt = re.sub(r"^[-*•]\s*", "", stripped).strip()
            txt = re.sub(r"\*\*(.*?)\*\*", r"\1", txt)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 60)
            pdf.set_x(15 + min(indent, 12))
            pdf.multi_cell(0, 6, f"  •  {txt}")

        # Numbered list
        elif re.match(r"^\d+[\.\)]\s", stripped):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 60)
            pdf.set_x(18)
            txt = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
            pdf.multi_cell(0, 6, txt)

        # Bold Q&A lines **Q:**
        elif stripped.startswith("**Q") or stripped.startswith("**A"):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(r, g, b)
            txt = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
            pdf.multi_cell(0, 7, txt)

        # Bold **key**: value lines
        elif "**" in stripped:
            txt = re.sub(r"\*\*(.*?)\*\*", r"[\1]", stripped)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 6, txt)

        # Normal text
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 6, stripped)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="smart_notes_")
    pdf.output(tmp.name)
    logger.info(f"PDF saved: {tmp.name}")
    return tmp.name
