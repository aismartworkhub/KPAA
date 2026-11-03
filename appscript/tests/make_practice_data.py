"""실습용 가상 데이터 생성 (실제 회원 정보 아님).

- 성명: 가명 형식(김*수), 등록번호: 실제 범위 밖(20001~), 이메일: example.com
- 실제 내려받은 파일의 특징을 일부러 재현: 첫 줄 제목행, 사무소명 끝 공백,
  공익 파일의 등록번호 열 이름이 '변리사', 공익 명단에 이미 이수한 사람 포함, 0.5시간 단위
사용: python make_practice_data.py <출력 xlsx> <출력 json>
"""
import json
import random
import sys
from datetime import datetime, timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

random.seed(20261104)
SUR = "김이박최정강조윤장임한오서신권황안송류홍"
MID = "민서지현준도하수영예우은재태성"
LAST = "수진호연우민아희원빈석준경철"


def fake_name():
    return f"{random.choice(SUR)}*{random.choice(LAST)}"


people = []
for i in range(60):
    reg = 20001 + i * 7
    people.append({"reg": reg, "name": fake_name(), "email": f"test{i + 1:02d}@example.com",
                   "phone": f"010-0000-{i + 1:04d}", "office": f"가상{random.choice(['특허', '국제특허', '특허법률'])}사무소{(i % 12) + 1}"})

wb = Workbook()
head_font = Font(bold=True)
fill = PatternFill("solid", fgColor="EEF2F8")

# 1) 추천신청 (구글폼 응답 형식)
ws = wb.active
ws.title = "추천신청"
ws.append(["타임스탬프", "추천기관", "성명", "등록번호", "이메일", "연락처", "소속사무소", "주요경력"])
orgs = ["국가철도공단", "국가지식재산위원회", "한국특허기술진흥원"]
start = datetime(2026, 10, 20, 9, 0)
apply_rows = []
for k, p in enumerate(people[:24]):
    apply_rows.append((orgs[k % 3], p))
apply_rows.append((orgs[1], people[2]))   # 여러 기관 중복
apply_rows.append((orgs[0], people[5]))   # 여러 기관 중복
apply_rows.append((orgs[0], people[9]))   # 같은 기관 두 번(people[9] 원래 orgs[0])
apply_rows.append((orgs[0], people[13]))  # 여러 기관
for k, (org, p) in enumerate(apply_rows):
    ws.append([(start + timedelta(hours=5 * k)).strftime("%Y-%m-%d %H:%M:%S"), org, p["name"], p["reg"], p["email"],
               p["phone"], p["office"], random.choice(["특허 심사 자문 5년", "상표 분쟁 대리 다수", "기술평가 위원 경력", "대학 산학협력 자문"])])

# 2) 메일양식
wt = wb.create_sheet("메일양식")
wt.append(["제목", "[대한변리사회] {추천기관} 추천 선정 안내"])
wt.append(["본문", "{성명} 회원님께\n\n회원님께서 신청하신 {추천기관} 추천 대상자로 선정되었음을 알려드립니다.\n"
                   "세부 일정은 추후 별도로 안내드리겠습니다.\n\n(등록번호 {등록번호})\n\n대한변리사회 회원서비스실 드림"])
wt.append(["안내", "{성명}, {추천기관}, {등록번호}, {소속사무소}처럼 [추천신청] 탭 1행의 열 이름을 중괄호로 감싸면 자동으로 바뀝니다."])
wt.column_dimensions["A"].width = 10
wt.column_dimensions["B"].width = 80
for r in range(1, 4):
    wt.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")

# 3) 연수 (첫 줄 제목행 + 사무소명 끝 공백)
wtr = wb.create_sheet("연수")
wtr.append(["7차 연수 미이수자(실습용 가상 데이터)"])
wtr.append(["연수주기", "등록번호", "성명", "사무소한글명"])
tr_people = people[0:30:2] + people[40:46]
for p in tr_people:
    wtr.append(["7차", p["reg"], p["name"], p["office"] + " "])

# 4) 공익 (열 이름 '변리사' = 등록번호, 이미 채운 사람·면제 포함)
wp = wb.create_sheet("공익")
wp.append(["공익활동 3주기 미이수자(실습용 가상 데이터)"])
wp.append(["차수", "성명", "변리사", "의무시간", "수행시간"])
pub = []
for i, p in enumerate(people):
    if i % 10 == 9:
        req, done = 0, random.choice([1, 3, 6])          # 면제
    elif i % 3 == 0:
        req, done = 24, random.choice([24, 25, 27.5])    # 이미 채움
    elif i % 3 == 1:
        req, done = 24, random.choice([0, 0, 3, 8.5])    # 미이수
    else:
        req, done = random.choice([10, 12, 18]), random.choice([0, 2, 4.5])
    pub.append(["3차", p["name"], p["reg"], req, done])
pub.sort(key=lambda r: -r[2])
for r in pub:
    wp.append(r)

# 5) 회비
wf = wb.create_sheet("회비")
wf.append(["등록번호", "성명", "미납액", "기준일"])
for p in people[1:36:3]:
    wf.append([p["reg"], p["name"], random.choice([150000, 300000, 450000]), "2026-11-01"])

for sheet in wb.worksheets:
    hr = 2 if sheet.title in ("연수", "공익") else 1
    if sheet.title != "메일양식":
        for c in sheet[hr]:
            c.font = head_font
            c.fill = fill
        for col in "ABCDEFGH":
            sheet.column_dimensions[col].width = 16

wb.save(sys.argv[1])

# 테스트용 JSON(시트별 2차원 배열)
out = {}
for sheet in wb.worksheets:
    out[sheet.title] = [[("" if v is None else v) for v in row] for row in sheet.iter_rows(values_only=True)]
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
print({k: len(v) for k, v in out.items()})
