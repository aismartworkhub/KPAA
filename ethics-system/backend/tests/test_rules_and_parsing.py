"""순수 로직 단위 테스트: 광고 스크리닝 규칙, 조문 파서, 기한 계산, 녹취 정리, 문서 추출."""
import zipfile
from datetime import date
from pathlib import Path

from app.services import ad_rules, doc_templates, minutes, reg_parser, text_extract, workflow

SEED = Path(__file__).resolve().parents[1] / "seed" / "regulations.txt"


def codes(text):
    return {f["rule_code"] for f in ad_rules.screen(text)}


def test_superlative_and_guarantee_detected():
    c = codes("국내 최고 특허사무소! 상표 등록 보장, 미등록 시 전액 환불")
    assert {"SUPERLATIVE", "GUARANTEE"} <= c


def test_success_rate_and_price():
    c = codes("특허 등록률 98.5% 달성, 상표출원 최저가 9,900원부터")
    assert {"SUCCESS_RATE", "FEE_PRICE"} <= c


def test_fake_title_and_comparison_and_prediction():
    c = codes("국제변리사 직접 상담. 타 사무소 대비 절반 비용. AI 등록 예측 서비스")
    assert {"FAKE_TITLE", "COMPARISON", "OUTCOME_PREDICTION"} <= c


def test_free_consultation_is_not_flagged():
    assert "FREE_BENEFIT" not in codes("무료 상담 가능합니다")
    assert "FREE_BENEFIT" in codes("상표 출원 수수료 무료 이벤트")


def test_clean_ad_has_no_high_findings():
    fs = ad_rules.screen("특허·상표 출원 전문. 대표 변리사 홍길동. 서울 서초구 소재. 상담 문의 02-000-0000")
    assert not [f for f in fs if f["confidence"] in ("HIGH", "MEDIUM")]


def test_responsible_name_heuristic():
    long_ad = "국내 최고 특허 서비스로 여러분의 아이디어를 지켜드립니다. 상표, 특허, 디자인 모두 가능합니다. 지금 바로 연락 주세요. 전국 어디서나 온라인으로 출원을 도와드립니다."
    assert "NO_RESPONSIBLE_NAME" in codes(long_ad)
    assert "NO_RESPONSIBLE_NAME" not in codes(long_ad + " 대표 변리사 홍길동")


def test_every_rule_reference_exists_in_regulations():
    arts = reg_parser.parse(SEED.read_text(encoding="utf-8"))
    keys = {(a["source"], a["article_no"]) for a in arts}
    for rule in ad_rules.RULES:
        for ref in rule.refs:
            assert (ref.source, ref.article_no) in keys, f"{rule.code} → {ref} 조문이 원문에 없음"


def test_parser_splits_all_sources():
    arts = reg_parser.parse(SEED.read_text(encoding="utf-8"))
    by = {}
    for a in arts:
        by.setdefault(a["source"], []).append(a)
    assert set(by) == {"PAA", "ETHICS", "ETHICS_COMMITTEE", "DISCIPLINE_COMMITTEE", "AD_REG"}
    ad7 = next(a for a in by["AD_REG"] if a["article_no"] == "제7조")
    assert "등록보장" in ad7["body"] and ad7["title"] == "주로 취급하는 업무광고"
    paa = {a["article_no"] for a in by["PAA"]}
    assert {"제8조의5", "제17조"} <= paa
    assert len({(a["source"], a["article_no"]) for a in arts}) == len(arts)  # 중복 없음


def test_parser_custom_source():
    arts = reg_parser.parse("제1조(목적) 이 규정은 테스트다.\n제2조 두번째 조문\n  ① 항 내용", "테스트 규정")
    assert [a["article_no"] for a in arts] == ["제1조", "제2조"]
    assert "항 내용" in arts[1]["body"]


def test_alerts():
    s = workflow.DEFAULT_SETTINGS
    today = date(2026, 10, 12)
    over = workflow.alerts_for({"status": "EXPLANATION_REQUESTED", "explanation_due": "2026-10-01"}, s, today)
    assert over[0]["code"] == "EXPLANATION_OVERDUE"
    disc = workflow.alerts_for({"status": "CORRECTION_ORDERED", "correction_due": "2026-08-01"}, s, today)
    assert disc[0]["code"] == "DISCIPLINE_ELIGIBLE"
    lim = workflow.alerts_for({"status": "REVIEW", "violation_date": "2023-12-01"}, s, today)
    assert lim[0]["code"] == "LIMITATION_SOON"
    nm = workflow.alerts_for({"status": "REVIEW", "respondent_is_member": 0}, s, today)
    assert nm[0]["code"] == "NON_MEMBER"


def test_transitions_table_is_consistent():
    for src, dsts in workflow.TRANSITIONS.items():
        assert src in workflow.STATUSES
        for d in dsts:
            assert d in workflow.STATUSES


def test_kdate_and_render_missing():
    assert doc_templates.kdate("2026-08-18") == "2026. 8. 18.(화)"
    text, missing = doc_templates.render("수신 {{respondent_office}} / {{doc_no}}", {"respondent_office": "가나"})
    assert text == "수신 가나 / {{확인 필요: 시행번호}}" and missing == ["시행번호"]


def test_minutes_rule_summary():
    t = "김위원장 00:01\n심의를 시작합니다.\n이위원 00:30\n등록률 표기는 제4조 제6호 위반 소지가 크다고 판단합니다.\n김위원장 01:00\n시정 요구하기로 의결하겠습니다. 찬성 3명 반대 0명입니다. 사무국은 결과를 통보하기로 합니다."
    r = minutes.summarize(t)
    names = [s["name"] for s in r["speakers"]]
    assert names == ["김위원장", "이위원"]
    assert any("의결" in x["text"] for x in r["resolutions"])
    assert any("통보" in x["text"] for x in r["follow_ups"])


def test_hwpx_and_txt_extraction(tmp_path):
    p = tmp_path / "a.hwpx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("Contents/section0.xml", '<hp:p><hp:run><hp:t>제1조(목적) 테스트 &amp; 확인</hp:t></hp:run></hp:p>')
    assert "테스트 & 확인" in text_extract.extract(p)[0][1]
    t = tmp_path / "b.txt"
    t.write_bytes("한글 CP949".encode("cp949"))
    assert text_extract.extract(t)[0][1] == "한글 CP949"
    chunks = text_extract.chunk([(1, "가" * 2000)], size=900, overlap=100)
    assert len(chunks) >= 2 and all(len(c[1]) <= 900 for c in chunks)
