/**
 * [1단계] 첫 자동화 — 시트 상단에 '회원업무' 메뉴를 만들고,
 *          버튼 하나로 선택한 칸에 오늘 날짜를 넣습니다.
 * 붙여넣는 곳: 확장 프로그램 > Apps Script > Code.gs (기존 내용을 모두 지우고 붙여넣기)
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🗂 회원업무')
    .addItem('오늘 날짜 넣기', 'addTodayDate')
    .addToUi();
}

/** 지금 선택한 칸에 오늘 날짜(예: 2026-11-04)를 넣습니다. */
function addTodayDate() {
  const cell = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet().getActiveCell();
  const today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  cell.setValue(today);
}
