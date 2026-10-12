"""사실관계 → 적용 조문·선례 후보 매칭.

근거는 오직 DB에 등록된 조문(articles)·선례(precedents)·사례집 조각(doc_chunks)이다.
"""
import sqlite3

from . import ad_rules, search
from .reg_parser import cite


def _articles_index(conn: sqlite3.Connection) -> search.Index:
    ver = tuple(conn.execute("SELECT COUNT(*), COALESCE(MAX(updated_at),'') FROM articles").fetchone())
    return search.cached_index("articles", ver, lambda: [
        (r["id"], f"{r['source_name']} {r['article_no']} {r['title'] or ''} {r['body']}")
        for r in conn.execute("SELECT id, source_name, article_no, title, body FROM articles")
        if not r["body"].lstrip().startswith("삭제") and not r["article_no"].startswith("부칙")])


def _precedents_index(conn: sqlite3.Connection) -> search.Index:
    ver = tuple(conn.execute("SELECT COUNT(*), COALESCE(MAX(updated_at),'') FROM precedents").fetchone())
    return search.cached_index("precedents", ver, lambda: [
        (r["id"], " ".join(filter(None, [r["title"], r["category"], r["facts"], r["holding"],
                                          r["related_rules"], r["keywords"], r["sanction_type"]])))
        for r in conn.execute("SELECT * FROM precedents")])


def _chunks_index(conn: sqlite3.Connection) -> search.Index:
    ver = tuple(conn.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM doc_chunks").fetchone())
    return search.cached_index("chunks", ver, lambda: [
        (r["id"], r["text"]) for r in conn.execute("SELECT id, text FROM doc_chunks")])


def article_by_ref(conn, source: str, article_no: str) -> dict | None:
    r = conn.execute("SELECT * FROM articles WHERE source=? AND article_no=?", (source, article_no)).fetchone()
    return dict(r) if r else None


def match_articles(conn: sqlite3.Connection, facts: str, top_k: int = 8, case_type: str | None = None) -> dict:
    findings = ad_rules.screen(facts) if case_type != "ETHICS" else []
    results: dict[int, dict] = {}

    for f in findings:
        for ref in f["refs"]:
            art = article_by_ref(conn, ref["source"], ref["article_no"])
            if not art:
                continue
            entry = results.setdefault(art["id"], {"article": art, "score": 0.0, "reasons": [], "items": set()})
            entry["score"] += 1.0 if f["confidence"] == "HIGH" else 0.7 if f["confidence"] == "MEDIUM" else 0.4
            entry["reasons"].append(f"규칙[{f['rule_label']}] '{f['matched_text']}'")
            if ref["item"]:
                entry["items"].add(ref["item"])

    for art_id, score, hits in _articles_index(conn).query(facts, top_k=top_k * 2, min_score=0.05):
        if art_id not in results:
            art = dict(conn.execute("SELECT * FROM articles WHERE id=?", (art_id,)).fetchone())
            results[art_id] = {"article": art, "score": 0.0, "reasons": [], "items": set()}
        results[art_id]["score"] += score
        results[art_id]["reasons"].append(f"문언 유사도 {score:.2f} (공통어: {', '.join(hits[:4])})")

    ranked = sorted(results.values(), key=lambda e: e["score"], reverse=True)[:top_k]
    return {
        "findings": findings,
        "articles": [{
            "id": e["article"]["id"], "source": e["article"]["source"], "citation": cite(e["article"]),
            "article_no": e["article"]["article_no"], "title": e["article"]["title"],
            "body": e["article"]["body"], "score": round(e["score"], 3),
            "items": sorted(e["items"]), "reasons": e["reasons"],
        } for e in ranked],
    }


def match_precedents(conn: sqlite3.Connection, text: str, top_k: int = 8) -> list[dict]:
    out = []
    for pid, score, hits in _precedents_index(conn).query(text, top_k=top_k):
        p = dict(conn.execute("SELECT * FROM precedents WHERE id=?", (pid,)).fetchone())
        p["score"] = round(score, 3)
        p["hits"] = hits
        out.append(p)
    return out


def search_chunks(conn: sqlite3.Connection, text: str, top_k: int = 10) -> list[dict]:
    out = []
    for cid, score, hits in _chunks_index(conn).query(text, top_k=top_k):
        r = dict(conn.execute(
            """SELECT c.id, c.page, c.text, d.id AS document_id, d.title AS document_title
               FROM doc_chunks c JOIN source_documents d ON d.id=c.document_id WHERE c.id=?""", (cid,)).fetchone())
        r["score"] = round(score, 3)
        r["hits"] = hits
        out.append(r)
    return out
