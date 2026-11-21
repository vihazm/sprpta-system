"""Draws the solution document (UC-L2-05): one A4 page with the case ID, the complaint summary and the verdict.

Case text can be English, Sinhala or Tamil, so the page uses Noto Sans with the Sinhala and Tamil faces as
fallbacks, and HarfBuzz shapes the letters so they join the way they should. The fonts are in app/assets/fonts.
"""

from datetime import datetime
from pathlib import Path

from fpdf import FPDF

FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
CRIMSON = (168, 16, 47)
INK = (22, 24, 29)
MUTED = (107, 114, 128)


def _fonts(pdf: FPDF) -> None:
    for family, file in (("Noto", "NotoSans"), ("NotoSinhala", "NotoSansSinhala"), ("NotoTamil", "NotoSansTamil")):
        pdf.add_font(family, "", FONTS / f"{file}-Regular.ttf")
        pdf.add_font(family, "B", FONTS / f"{file}-Bold.ttf")
    pdf.set_fallback_fonts(["NotoSinhala", "NotoTamil"])
    pdf.set_text_shaping(True)


def _section(pdf: FPDF, heading: str, text: str) -> None:
    pdf.ln(4)
    pdf.set_font("Noto", "B", 11)
    pdf.set_text_color(*CRIMSON)
    pdf.cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Noto", "", 10.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5.6, text, align="L", new_x="LMARGIN", new_y="NEXT")


def render(
    *,
    reference: str,
    area: str,
    vehicle: str,
    officer: str,
    generated_at: datetime,
    summary: str,
    verdict: str,
    reasoning: str,
    solution_details: str,
) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_title(f"Solution document {reference}")
    pdf.set_margins(20, 18, 20)
    pdf.set_auto_page_break(True, margin=18)
    _fonts(pdf)
    pdf.add_page()

    pdf.set_font("Noto", "B", 9)
    pdf.set_text_color(*CRIMSON)
    pdf.cell(0, 5, "SOUTHERN PROVINCIAL ROAD PASSENGER TRANSPORT AUTHORITY", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Noto", "B", 20)
    pdf.set_text_color(*INK)
    pdf.cell(0, 12, "Solution document", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*CRIMSON)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
    pdf.ln(5)

    facts = [
        ("Case reference", reference),
        ("Area", area),
        ("Vehicle", vehicle),
        ("Decided by", officer),
        ("Date", generated_at.strftime("%d %B %Y, %H:%M")),
    ]
    for label, value in facts:
        pdf.set_font("Noto", "", 9.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(38, 6.5, label)
        pdf.set_font("Noto", "B", 10.5)
        pdf.set_text_color(*INK)
        pdf.cell(0, 6.5, value, new_x="LMARGIN", new_y="NEXT")

    _section(pdf, "Complaint summary", summary)
    _section(pdf, "Verdict", verdict)
    _section(pdf, "Reasoning", reasoning)
    _section(pdf, "Solution to carry out", solution_details)

    pdf.ln(8)
    pdf.set_font("Noto", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        0,
        5,
        align="L",
        text=
        "Give this document to the implementing staff through official channels. When the work is done, they mark "
        f"case {reference} as done in the SPRPTA system, and the area officer approves it to close the case.",
    )
    return bytes(pdf.output())
