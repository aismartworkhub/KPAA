"""공문·회의자료를 .docx 로 내보낸다(한글/워드에서 열어 최종 편집·직인 처리)."""
import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, Cm

FONT = "맑은 고딕"


def _style(doc: Document):
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(2.0)
        s.left_margin = s.right_margin = Cm(2.2)


def text_to_docx(text: str, title_line: str | None = None) -> bytes:
    doc = Document()
    _style(doc)
    if title_line:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(title_line)
        r.bold = True
        r.font.size = Pt(18)
    for line in text.splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if indent:
            p.paragraph_format.left_indent = Cm(0.35 * indent)
        if line.strip() == "대한변리사회장":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(stripped)
            run.bold = True
            run.font.size = Pt(16)
            continue
        p.add_run(stripped)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
