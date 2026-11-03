"""법령·회규 조문, 징계 선례, 사례집 원문(업로드) 관리와 검색."""
import csv
import io
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from .. import audit, db
from ..deps import client_ip, current_user, get_db, require_admin, require_staff
from ..seed import load_articles
from ..services import llm, matcher, search, storage, text_extract
from ..services.reg_parser import SOURCE_LABELS, cite
from .cases import run_analysis

router = APIRouter(prefix="/api", tags=["knowledge"])


class MatchIn(BaseModel):
    facts: str = Field(min_length=2, max_length=50000)
    case_type: str | None = Field(default=None, pattern="^(AD|ETHICS)$")
    use_ai: bool = False


class ArticleUpdate(BaseModel):
    title: str | None = None
    body: str = Field(min_length=1)


class PrecedentIn(BaseModel):
    origin: str = Field(default="KBA", pattern="^(KBA|KPAA|OTHER|DEMO)$")
    volume: str | None = None
    case_ref: str | None = None
    title: str = Field(min_length=2, max_length=300)
    decided_on: str | None = None
    category: str | None = None
    sanction_type: str | None = None
    sanction_detail: str | None = None
    facts: str | None = None
    holding: str | None = None
    related_rules: str | None = None
    keywords: str | None = None
    source_document_id: int | None = None
    source_page: int | None = None


class SearchIn(BaseModel):
    text: str = Field(min_length=2, max_length=20000)
    top_k: int = 10


class ExtractIn(BaseModel):
    chunk_ids: list[int] = Field(min_length=1, max_length=20)
    use_ai: bool = False


# ── 조문 ─────────────────────────────────────────────────────────────
@router.get("/articles/sources")
def article_sources(user=Depends(current_user), conn=Depends(get_db)):
    return db.rows(conn.execute(
        "SELECT source, source_name, COUNT(*) AS count, MAX(updated_at) AS updated_at FROM articles GROUP BY source, source_name ORDER BY MIN(id)"))


@router.get("/articles")
def list_articles(source: str | None = None, q: str | None = None, user=Depends(current_user), conn=Depends(get_db)):
    where, args = [], []
    if source:
        where.append("source=?"); args.append(source)
    if q:
        where.append("(article_no LIKE ? OR title LIKE ? OR body LIKE ?)")
        args += [f"%{q}%"] * 3
    w = ("WHERE " + " AND ".join(where)) if where else ""
    items = db.rows(conn.execute(f"SELECT * FROM articles {w} ORDER BY source, sort_order LIMIT 500", args))
    for a in items:
        a["citation"] = cite(a)
    return items


@router.get("/articles/{aid}")
def get_article(aid: int, user=Depends(current_user), conn=Depends(get_db)):
    a = db.one(conn.execute("SELECT * FROM articles WHERE id=?", (aid,)))
    if not a:
        raise HTTPException(404, "조문을 찾을 수 없습니다.")
    a["citation"] = cite(a)
    return a


@router.put("/articles/{aid}")
def update_article(aid: int, body: ArticleUpdate, request: Request, admin=Depends(require_admin), conn=Depends(get_db)):
    a = db.one(conn.execute("SELECT * FROM articles WHERE id=?", (aid,)))
    if not a:
        raise HTTPException(404, "조문을 찾을 수 없습니다.")
    conn.execute("UPDATE articles SET title=?, body=?, updated_at=datetime('now','localtime') WHERE id=?",
                 (body.title, body.body, aid))
    audit.log(conn, admin["id"], "article.update", "article", aid, {"before": a["body"][:500]}, client_ip(request))
    return {"ok": True}


@router.post("/articles/match")
def match(body: MatchIn, request: Request, user=Depends(current_user), conn=Depends(get_db)):
    return run_analysis(conn, body.facts, body.case_type, body.use_ai, user, request)


@router.post("/articles/import")
async def import_articles(request: Request, file: UploadFile = File(...), source_name: str | None = Form(None),
                          admin=Depends(require_admin), conn=Depends(get_db)):
    """개정 법령·회규 원문 업로드(HWP/HWPX/DOCX/TXT/PDF). '< 규정명 >' 머리표가 없으면 source_name 필요."""
    meta = await storage.save_upload(file, "regulations", {".hwp", ".hwpx", ".docx", ".txt", ".pdf"})
    path = storage.resolve(meta["stored_path"])
    try:
        text = "\n".join(t for _, t in text_extract.extract(path))
    except text_extract.ExtractError as e:
        raise HTTPException(400, str(e))
    if not re.search(r"^\s*<\s*.+?\s*>\s*$", text, re.M) and not source_name:
        raise HTTPException(400, "문서에 '< 규정명 >' 머리표가 없습니다. 규정명을 입력하세요.")
    result = load_articles(conn, text, source_name)
    if not result["count"]:
        raise HTTPException(400, "조문(제N조)을 찾지 못했습니다. 원문 형식을 확인하세요.")
    conn.execute("INSERT INTO source_documents(kind, title, filename, stored_path, sha256, size, uploaded_by) VALUES (?,?,?,?,?,?,?)",
                 ("regulation", source_name or ", ".join(result["sources"]), meta["file_name"], meta["stored_path"],
                  meta["sha256"], meta["size"], admin["id"]))
    search.clear_cache()
    audit.log(conn, admin["id"], "article.import", "article", None, result, client_ip(request))
    return result


# ── 선례 ─────────────────────────────────────────────────────────────
@router.get("/precedents")
def list_precedents(q: str | None = None, origin: str | None = None, sanction_type: str | None = None,
                    category: str | None = None, user=Depends(current_user), conn=Depends(get_db)):
    where, args = [], []
    for col, v in (("origin", origin), ("sanction_type", sanction_type), ("category", category)):
        if v:
            where.append(f"{col}=?"); args.append(v)
    if q:
        where.append("(title LIKE ? OR facts LIKE ? OR holding LIKE ? OR keywords LIKE ? OR related_rules LIKE ? OR case_ref LIKE ?)")
        args += [f"%{q}%"] * 6
    w = ("WHERE " + " AND ".join(where)) if where else ""
    return db.rows(conn.execute(f"SELECT * FROM precedents {w} ORDER BY id DESC LIMIT 500", args))


@router.get("/precedents/facets")
def precedent_facets(user=Depends(current_user), conn=Depends(get_db)):
    return {
        "sanction_types": [r[0] for r in conn.execute("SELECT DISTINCT sanction_type FROM precedents WHERE sanction_type IS NOT NULL AND sanction_type<>'' ORDER BY 1")],
        "categories": [r[0] for r in conn.execute("SELECT DISTINCT category FROM precedents WHERE category IS NOT NULL AND category<>'' ORDER BY 1")],
        "stats": db.rows(conn.execute("SELECT sanction_type, COUNT(*) n FROM precedents GROUP BY sanction_type ORDER BY n DESC")),
    }


@router.post("/precedents")
def create_precedent(body: PrecedentIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    data = body.model_dump()
    cols = list(data)
    pid = conn.execute(f"INSERT INTO precedents({', '.join(cols)}, created_by) VALUES ({','.join('?' * len(cols))}, ?)",
                       (*data.values(), user["id"])).lastrowid
    audit.log(conn, user["id"], "precedent.create", "precedent", pid, None, client_ip(request))
    return {"id": pid}


@router.get("/precedents/{pid}")
def get_precedent(pid: int, user=Depends(current_user), conn=Depends(get_db)):
    p = db.one(conn.execute("SELECT * FROM precedents WHERE id=?", (pid,)))
    if not p:
        raise HTTPException(404, "선례를 찾을 수 없습니다.")
    return p


@router.put("/precedents/{pid}")
def update_precedent(pid: int, body: PrecedentIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM precedents WHERE id=?", (pid,)).fetchone():
        raise HTTPException(404, "선례를 찾을 수 없습니다.")
    data = body.model_dump()
    conn.execute(f"UPDATE precedents SET {', '.join(k + '=?' for k in data)}, updated_at=datetime('now','localtime') WHERE id=?",
                 (*data.values(), pid))
    audit.log(conn, user["id"], "precedent.update", "precedent", pid, None, client_ip(request))
    return {"ok": True}


@router.delete("/precedents/{pid}")
def delete_precedent(pid: int, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    conn.execute("DELETE FROM precedents WHERE id=?", (pid,))
    audit.log(conn, user["id"], "precedent.delete", "precedent", pid, None, client_ip(request))
    return {"ok": True}


CSV_COLUMNS = ["origin", "volume", "case_ref", "title", "decided_on", "category", "sanction_type", "sanction_detail",
               "facts", "holding", "related_rules", "keywords"]


@router.post("/precedents/import-csv")
async def import_precedents_csv(request: Request, file: UploadFile = File(...), user=Depends(require_staff), conn=Depends(get_db)):
    raw = await file.read()
    text = None
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc); break
        except UnicodeDecodeError:
            pass
    if text is None:
        raise HTTPException(400, "CSV 인코딩을 판별할 수 없습니다.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "title" not in reader.fieldnames:
        raise HTTPException(400, f"CSV 머리행에 title 열이 필요합니다. 사용 가능한 열: {', '.join(CSV_COLUMNS)}")
    n, skipped = 0, 0
    with db.transaction(conn):
        for row in reader:
            data = {c: (row.get(c) or "").strip() or None for c in CSV_COLUMNS}
            if not data["title"]:
                skipped += 1; continue
            data["origin"] = data["origin"] if data["origin"] in ("KBA", "KPAA", "OTHER") else "KBA"
            conn.execute(f"INSERT INTO precedents({', '.join(CSV_COLUMNS)}, created_by) VALUES ({','.join('?' * len(CSV_COLUMNS))}, ?)",
                         (*data.values(), user["id"]))
            n += 1
        audit.log(conn, user["id"], "precedent.import_csv", "precedent", None, {"imported": n}, client_ip(request))
    return {"imported": n, "skipped": skipped}


@router.post("/precedents/search")
def search_precedents(body: SearchIn, user=Depends(current_user), conn=Depends(get_db)):
    k = max(1, min(body.top_k, 30))
    return {"precedents": matcher.match_precedents(conn, body.text, k), "passages": matcher.search_chunks(conn, body.text, k)}


# ── 사례집 원문(업로드) ───────────────────────────────────────────────
@router.get("/source-docs")
def list_docs(kind: str | None = None, user=Depends(current_user), conn=Depends(get_db)):
    if kind:
        return db.rows(conn.execute("SELECT * FROM source_documents WHERE kind=? ORDER BY id DESC", (kind,)))
    return db.rows(conn.execute("SELECT * FROM source_documents ORDER BY id DESC"))


@router.post("/source-docs")
async def upload_doc(request: Request, file: UploadFile = File(...), title: str = Form(...),
                     kind: str = Form("precedent_book"), user=Depends(require_staff), conn=Depends(get_db)):
    if kind not in ("precedent_book", "meeting", "other"):
        raise HTTPException(400, "kind 값이 올바르지 않습니다.")
    meta = await storage.save_upload(file, "books", {".pdf", ".hwp", ".hwpx", ".docx", ".txt"})
    dup = db.one(conn.execute("SELECT id, title FROM source_documents WHERE sha256=?", (meta["sha256"],)))
    if dup:
        storage.resolve(meta["stored_path"]).unlink(missing_ok=True)
        raise HTTPException(409, f"같은 파일이 이미 등록되어 있습니다: {dup['title']}")
    try:
        pages = text_extract.extract(storage.resolve(meta["stored_path"]))
    except text_extract.ExtractError as e:
        raise HTTPException(400, str(e))
    chunks = text_extract.chunk(pages)
    with db.transaction(conn):
        did = conn.execute(
            """INSERT INTO source_documents(kind, title, filename, stored_path, sha256, size, pages, chunk_count, uploaded_by)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (kind, title, meta["file_name"], meta["stored_path"], meta["sha256"], meta["size"],
             len(pages) if pages and pages[0][0] is not None else None, len(chunks), user["id"])).lastrowid
        conn.executemany("INSERT INTO doc_chunks(document_id, page, seq, text) VALUES (?,?,?,?)",
                         [(did, p, i, t) for i, (p, t) in enumerate(chunks)])
        audit.log(conn, user["id"], "source_doc.upload", "source_document", did, {"chunks": len(chunks)}, client_ip(request))
    return {"id": did, "chunks": len(chunks), "pages": len(pages)}


@router.delete("/source-docs/{did}")
def delete_doc(did: int, request: Request, admin=Depends(require_admin), conn=Depends(get_db)):
    d = db.one(conn.execute("SELECT * FROM source_documents WHERE id=?", (did,)))
    if not d:
        raise HTTPException(404, "문서를 찾을 수 없습니다.")
    conn.execute("DELETE FROM source_documents WHERE id=?", (did,))
    try:
        storage.resolve(d["stored_path"]).unlink(missing_ok=True)
    except HTTPException:
        pass
    audit.log(conn, admin["id"], "source_doc.delete", "source_document", did, {"title": d["title"]}, client_ip(request))
    return {"ok": True}


@router.get("/source-docs/{did}/chunks")
def doc_chunks(did: int, q: str | None = None, page: int | None = None, user=Depends(current_user), conn=Depends(get_db)):
    where, args = ["document_id=?"], [did]
    if q:
        where.append("text LIKE ?"); args.append(f"%{q}%")
    if page:
        where.append("page=?"); args.append(page)
    return db.rows(conn.execute(f"SELECT * FROM doc_chunks WHERE {' AND '.join(where)} ORDER BY seq LIMIT 200", args))


SANCTION_RE = re.compile(r"(영구\s*제명|제명|정직\s*\d+\s*(?:개월|월|년)|과태료\s*[\d,]+\s*(?:만\s*)?원|견책|경고|불문|기각|무혐의|업무정지\s*\d+\s*(?:개월|월|년))")
CASEREF_RE = re.compile(r"(변협\s*\d{4}\s*[-‐]?\s*\d+|법무부\s*\d{4}\s*[-‐]?\s*\d+|\d{4}\s*[-‐]\s*\d{1,4}\s*호?|\d{4}\s*징\s*\d+)")


@router.post("/source-docs/extract")
def extract_cases(body: ExtractIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    """선택한 원문 조각에서 사례 후보 추출 → 담당자 검토 후 '선례 등록'. AI 미사용 시 규칙 기반 후보."""
    q = ",".join("?" * len(body.chunk_ids))
    chunks = db.rows(conn.execute(
        f"""SELECT c.*, d.title AS doc_title FROM doc_chunks c JOIN source_documents d ON d.id=c.document_id
            WHERE c.id IN ({q}) ORDER BY c.document_id, c.seq""", body.chunk_ids))
    if not chunks:
        raise HTTPException(404, "선택한 조각을 찾을 수 없습니다.")
    text = "\n\n".join(c["text"] for c in chunks)
    base = {"source_document_id": chunks[0]["document_id"], "source_page": chunks[0]["page"], "volume": chunks[0]["doc_title"]}
    if body.use_ai:
        if not llm.available():
            raise HTTPException(400, "AI 기능이 설정되지 않았습니다(ANTHROPIC_API_KEY).")
        try:
            cands = llm.extract_precedents(text)
        except llm.LLMError as e:
            raise HTTPException(502, str(e))
        audit.log(conn, user["id"], "ai.extract_precedents", "source_document", base["source_document_id"],
                  {"candidates": len(cands)}, client_ip(request))
        return {"method": "ai", "candidates": [{**base, **c} for c in cands]}
    sanctions = list(dict.fromkeys(m.group(0) for m in SANCTION_RE.finditer(text)))
    refs = list(dict.fromkeys(m.group(0) for m in CASEREF_RE.finditer(text)))
    first_line = next((ln.strip() for ln in text.splitlines() if len(ln.strip()) > 8), "")[:120]
    sentences = re.split(r"(?<=[.다])\s+", text)
    holding = " ".join(s for s in sentences if re.search(r"(인정|판단|해당|위반|징계)", s))[:800]
    return {"method": "rule", "candidates": [{
        **base, "case_ref": refs[0] if refs else "", "title": first_line, "category": "",
        "sanction_type": sanctions[0] if sanctions else "미기재", "sanction_detail": ", ".join(sanctions[:5]),
        "facts": text[:1500], "holding": holding, "related_rules": "", "verified": True,
    }], "notice": "규칙 기반 후보입니다. 제목·요지·징계수위를 원문과 대조해 수정한 뒤 등록하세요."}
