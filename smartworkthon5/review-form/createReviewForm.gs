/**
 * 제5회 스마트워크톤 후기 이벤트 — 구글폼 자동 생성 스크립트
 *
 * 사용법 (1분)
 *  1. https://script.google.com 접속 → [새 프로젝트]
 *  2. 기존 코드를 지우고 이 파일 내용을 전부 붙여넣기 → 저장(Ctrl+S)
 *  3. 위쪽 함수 선택이 createReviewForm 인지 확인 → [실행]
 *  4. 처음 한 번 "권한 검토" → 내 계정 선택 → (고급) → 이동 → 허용
 *  5. 아래 [실행 로그]에 나오는 "QR용 짧은 주소"(forms.gle/…)를 복사해서 Claude에게 보내기
 *
 * 만들어지는 것
 *  - 구글폼: 「제5회 스마트워크톤 후기 이벤트 신청」
 *  - 응답 시트: 「제5회 스마트워크톤 후기 이벤트 신청 (응답)」 — 선물 발송 명단으로 사용
 *
 * 경품·마감일을 바꾸려면 아래 CONFIG 만 고친 뒤 실행하세요.
 */
const CONFIG = {
  title: '제5회 스마트워크톤 후기 이벤트 신청',
  deadline: '2026년 11월 27일(금) 23:59',       // 신청 마감
  event1: { name: 'EVENT 01 · SNS 후기', rule: '사진 3장 이상 + 100자 이상', gift: '스타벅스 아메리카노 모바일 쿠폰' },
  event2: { name: 'EVENT 02 · 블로그·카페 후기', rule: '사진 5장 이상 + 1,000자 이상', gift: '치킨 + 콜라 1.25L 모바일 쿠폰' },
  hashtags: '#제5회스마트워크톤 #스마트워크톤 #AISH',
  host: '에이아이스마트워크허브(AISH)',
};

function createReviewForm() {
  const c = CONFIG;
  const form = FormApp.create(c.title);
  form.setDescription(
    '제5회 스마트워크톤(2026. 11. 20, G밸리 기업시민청)에 함께해 주셔서 감사합니다!\n' +
    '후기를 올리신 뒤 이 신청서를 작성하시면, 선물을 행사 후 모바일 쿠폰으로 보내 드립니다.\n\n' +
    '■ ' + c.event1.name + ' — ' + c.event1.rule + ' → ' + c.event1.gift + '\n' +
    '■ ' + c.event2.name + ' — ' + c.event2.rule + ' → ' + c.event2.gift + '\n\n' +
    '■ 해시태그: ' + c.hashtags + '\n' +
    '■ 신청 마감: ' + c.deadline + '\n\n' +
    '※ 커피와 치킨은 중복 지급되지 않습니다. (한 분당 1개)\n' +
    '※ 후기는 "전체 공개"로 올려 주세요. 비공개·삭제된 후기는 확인이 어려워 제외됩니다.\n' +
    '※ 후기 내용이 행사와 무관하거나 조건에 맞지 않으면 지급 대상에서 제외될 수 있습니다.\n' +
    '※ 경품은 사정에 따라 동급의 다른 상품으로 바뀔 수 있습니다.\n\n' +
    '주최 ' + c.host
  );
  form.setCollectEmail(false);
  form.setProgressBar(false);
  form.setAllowResponseEdits(false);
  form.setConfirmationMessage(
    '신청이 완료되었습니다. 감사합니다!\n' +
    '후기를 확인한 뒤, 적어 주신 휴대폰 번호로 모바일 쿠폰을 보내 드릴게요.'
  );

  form.addTextItem().setTitle('이름').setRequired(true);

  form.addTextItem()
    .setTitle('휴대폰 번호')
    .setHelpText('모바일 쿠폰을 받을 번호입니다. 예) 010-1234-5678')
    .setValidation(FormApp.createTextValidation()
      .requireTextMatchesPattern('^01[016789]-?\\d{3,4}-?\\d{4}$')
      .setHelpText('휴대폰 번호 형식으로 입력해 주세요. 예) 010-1234-5678')
      .build())
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('오늘 어떻게 참여하셨나요?')
    .setChoiceValues(['경진대회 참가자', '참관객'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('참여한 이벤트')
    .setHelpText('한 분당 1개만 지급됩니다. 두 가지 모두 하셨다면 EVENT 02를 선택해 주세요.')
    .setChoiceValues([
      c.event1.name + ' (' + c.event1.rule + ') → ' + c.event1.gift,
      c.event2.name + ' (' + c.event2.rule + ') → ' + c.event2.gift,
    ])
    .setRequired(true);

  form.addTextItem()
    .setTitle('후기 게시물 주소(링크)')
    .setHelpText('올린 후기의 주소를 붙여넣어 주세요. 인스타그램은 게시물 ⋯ → 링크 복사')
    .setValidation(FormApp.createTextValidation()
      .requireTextIsUrl()
      .setHelpText('https:// 로 시작하는 주소를 붙여넣어 주세요.')
      .build())
    .setRequired(true);

  form.addTextItem()
    .setTitle('SNS·블로그 아이디 (선택)')
    .setHelpText('후기 확인이 어려울 때 찾아보기 위해 사용합니다.');

  form.addMultipleChoiceItem()
    .setTitle('개인정보 수집·이용 동의')
    .setHelpText(
      '· 수집 항목: 이름, 휴대폰 번호, 후기 링크, SNS 아이디\n' +
      '· 이용 목적: 후기 확인 및 경품(모바일 쿠폰) 발송\n' +
      '· 보유 기간: 경품 발송 완료 후 1개월 이내 파기\n' +
      '· 동의하지 않으실 수 있으나, 이 경우 경품을 받으실 수 없습니다.'
    )
    .setChoiceValues(['동의합니다'])
    .setRequired(true);

  // 응답 시트(선물 발송 명단)
  const ss = SpreadsheetApp.create(c.title + ' (응답)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  const url = form.getPublishedUrl();
  let short = url;
  try { short = form.shortenFormUrl(url); } catch (e) { /* 짧은 주소 실패 시 긴 주소 사용 */ }

  Logger.log('==============================================');
  Logger.log('QR용 짧은 주소 (이것을 Claude에게 보내 주세요): ' + short);
  Logger.log('응답 화면 주소: ' + url);
  Logger.log('폼 편집 주소: ' + form.getEditUrl());
  Logger.log('응답 시트(발송 명단): ' + ss.getUrl());
  Logger.log('==============================================');
}
