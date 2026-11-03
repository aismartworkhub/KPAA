"""업로드 문서(HWP·HWPX·PDF·DOCX·TXT)에서 텍스트를 추출한다.

반환: [(page_or_None, text), ...]  — PDF는 쪽 단위, 나머지는 단일 블록.
"""
import html
import re
import struct
import zipfile
import zlib
from pathlib import Path


class ExtractError(Exception):
    pass


def _hwp(path: Path) -> str:
    import olefile
    if not olefile.isOleFile(str(path)):
        raise ExtractError("HWP(5.0) 형식이 아닙니다.")
    ole = olefile.OleFileIO(str(path))
    try:
        header = ole.openstream("FileHeader").read()
        if header[36] & 0x02:
            raise ExtractError("암호가 걸린 HWP 파일은 읽을 수 없습니다.")
        compressed = bool(header[36] & 0x01)
        sections = sorted((s for s in ole.listdir() if s[0] == "BodyText"),
                          key=lambda s: int(s[1].replace("Section", "")))
        out = []
        for s in sections:
            data = ole.openstream(s).read()
            if compressed:
                data = zlib.decompress(data, -15)
            out.append(_hwp_records(data))
        return "".join(out)
    finally:
        ole.close()


# HWP 제어문자: 인라인/확장 컨트롤은 8 WCHAR(16바이트)를 차지한다.
_EXT_CTRL = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}


def _hwp_records(data: bytes) -> str:
    out = []
    i = 0
    n = len(data)
    while i + 4 <= n:
        header = struct.unpack_from("<I", data, i)[0]
        i += 4
        tag = header & 0x3FF
        size = (header >> 20) & 0xFFF
        if size == 0xFFF:
            size = struct.unpack_from("<I", data, i)[0]
            i += 4
        if tag == 67:  # HWPTAG_PARA_TEXT
            raw = data[i:i + size]
            j = 0
            chars = []
            while j + 2 <= len(raw):
                c = struct.unpack_from("<H", raw, j)[0]
                if c in _EXT_CTRL:
                    if c == 9:
                        chars.append("\t")
                    j += 16
                    continue
                if c in (10, 13):
                    chars.append("\n")
                elif c >= 32:
                    chars.append(chr(c))
                j += 2
            out.append("".join(chars))
        i += size
    return "".join(out)


def _hwpx(path: Path) -> str:
    try:
        z = zipfile.ZipFile(str(path))
    except zipfile.BadZipFile as e:
        raise ExtractError("HWPX 형식이 아닙니다.") from e
    names = sorted(n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n))
    out = []
    for name in names:
        xml = z.read(name).decode("utf-8", errors="replace")
        for para in re.split(r"</hp:p>", xml):
            t = "".join(re.findall(r"<hp:t(?:\s[^>]*)?>([^<]*)</hp:t>", para))
            if t.strip():
                out.append(html.unescape(t))
    return "\n".join(out)


def _docx(path: Path) -> str:
    import docx
    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    return "\n".join(parts)


def _pdf(path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader
    try:
        reader = PdfReader(str(path))
    except Exception as e:  # pypdf는 다양한 예외를 던진다
        raise ExtractError(f"PDF를 열 수 없습니다: {e}") from e
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as e:
            raise ExtractError("암호가 걸린 PDF는 읽을 수 없습니다.") from e
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            pages.append((idx, page.extract_text() or ""))
        except Exception:
            pages.append((idx, ""))
    return pages


def extract(path: Path) -> list[tuple[int | None, str]]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        pages = _pdf(path)
        if not any(t.strip() for _, t in pages):
            raise ExtractError("PDF에서 텍스트를 찾지 못했습니다(스캔 이미지 PDF는 OCR 후 업로드하세요).")
        return pages
    if ext == ".hwp":
        return [(None, _hwp(path))]
    if ext == ".hwpx":
        return [(None, _hwpx(path))]
    if ext == ".docx":
        return [(None, _docx(path))]
    if ext in (".txt", ".csv", ".md"):
        raw = path.read_bytes()
        for enc in ("utf-8-sig", "cp949"):
            try:
                return [(None, raw.decode(enc))]
            except UnicodeDecodeError:
                continue
        raise ExtractError("텍스트 인코딩을 판별할 수 없습니다(UTF-8 또는 CP949).")
    raise ExtractError(f"지원하지 않는 형식입니다: {ext}")


def chunk(pages: list[tuple[int | None, str]], size: int = 900, overlap: int = 150) -> list[tuple[int | None, str]]:
    """검색용 조각으로 나눈다. 문단 경계를 우선 사용하고 길면 자른다."""
    chunks = []
    for page, text in pages:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            if end < len(text):
                cut = text.rfind("\n", start + size // 2, end)
                if cut > 0:
                    end = cut
            piece = text[start:end].strip()
            if piece:
                chunks.append((page, piece))
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks
