"""공문 메일 발송(SMTP). 발송 결과(Message-ID)는 사건 기록에 근거로 남는다."""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from .. import config


class MailError(Exception):
    pass


def configured() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_FROM)


def send(to: str, subject: str, body: str, attachment: tuple[str, bytes] | None = None) -> str:
    if not configured():
        raise MailError("메일 서버(SMTP)가 설정되지 않았습니다.")
    msg = EmailMessage()
    msg["From"] = config.SMTP_FROM
    msg["To"] = to
    if config.SMTP_BCC_SELF:
        msg["Bcc"] = config.SMTP_FROM
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg_id = make_msgid(domain=config.SMTP_FROM.split("@")[-1])
    msg["Message-ID"] = msg_id
    msg.set_content(body)
    if attachment:
        name, data = attachment
        msg.add_attachment(data, maintype="application",
                           subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename=name)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as s:
            if config.SMTP_STARTTLS:
                s.starttls(context=ssl.create_default_context())
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD or "")
            s.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(f"메일 발송 실패: {e}") from e
    return msg_id
