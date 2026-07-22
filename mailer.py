"""Gmail SMTP로 실제 메일을 발송한다. (email_server.py의 send_email 로직 기반)

법적 준수: 제목에 (광고) 접두, 본문 하단에 수신거부 안내를 자동 부착한다.
"""
import smtplib
from email.message import EmailMessage

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

UNSUBSCRIBE_NOTICE = (
    "\n\n──────────────\n"
    "본 메일은 수신에 동의하신 분께만 발송됩니다.\n"
    "수신을 원치 않으시면 본 메일에 '수신거부'라고 회신해 주세요.\n"
)


def with_ad_prefix(subject: str) -> str:
    """제목 앞에 (광고) 표기를 붙인다. 이미 있으면 그대로 둔다."""
    subject = (subject or "").strip()
    return subject if subject.startswith("(광고)") else f"(광고) {subject}"


def with_unsubscribe(body: str) -> str:
    return (body or "").rstrip() + UNSUBSCRIBE_NOTICE


def send_gmail(sender_email, app_password, to_email, subject, body, sender_name=None):
    """Gmail 계정으로 1건 발송. 실패 시 예외를 던진다.

    sender_email : 보내는 Gmail 주소
    app_password : Gmail 앱 비밀번호 (일반 비밀번호 아님)
    """
    full_subject = with_ad_prefix(subject)
    full_body = with_unsubscribe(body)

    msg = EmailMessage()
    msg["Subject"] = full_subject
    msg["From"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
    msg["To"] = to_email
    msg.set_content(full_body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)

    return full_subject
