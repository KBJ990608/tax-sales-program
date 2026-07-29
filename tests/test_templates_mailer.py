"""템플릿 치환과 법정 표기 부착 테스트 (templates.py, mailer.py)."""
import pytest

import mailer
import templates


# ── 템플릿 ────────────────────────────────────────────────────────────────
def test_five_templates_exist():
    names = templates.template_names()
    assert len(names) == 5
    assert set(names) == {"환영", "개업축하", "기장대행", "법인결산", "연말정산"}


@pytest.mark.parametrize("name", templates.template_names())
def test_every_template_substitutes_all_placeholders(name):
    """어떤 템플릿도 {업체명}/{대표자}를 남기면 안 된다."""
    subject, body = templates.render(name, "행복상사", "홍길동")
    for text in (subject, body):
        assert "{업체명}" not in text
        assert "{대표자}" not in text
    assert "행복상사" in subject + body


@pytest.mark.parametrize("name", templates.template_names())
def test_template_source_has_no_ad_prefix_or_unsubscribe(name):
    """(광고)와 수신거부 문구는 mailer가 붙이므로 템플릿에 있으면 중복된다."""
    t = templates.TEMPLATES[name]
    assert not t["제목"].startswith("(광고)")
    assert "수신거부" not in t["본문"]


def test_render_falls_back_when_names_blank():
    subject, body = templates.render("환영", "", "")
    assert "사장님" in subject or "사장님" in body
    assert "대표" in body


def test_render_raw_substitutes_ai_template():
    subject, body = templates.render_raw(
        "{업체명} 안내", "{대표자}님 안녕하세요. {업체명} 관련 건입니다.", "행복상사", "홍길동"
    )
    assert subject == "행복상사 안내"
    assert body == "홍길동님 안녕하세요. 행복상사 관련 건입니다."


def test_render_raw_leaves_unknown_braces_alone():
    """치환 대상이 아닌 중괄호는 KeyError 없이 그대로 남아야 한다."""
    subject, body = templates.render_raw("{업체명}", "{알수없는키} 와 {대표자}", "A", "가")
    assert body == "{알수없는키} 와 가"


# ── 법정 표기 ─────────────────────────────────────────────────────────────
def test_ad_prefix_added():
    assert mailer.with_ad_prefix("세무 안내") == "(광고) 세무 안내"


def test_ad_prefix_not_duplicated():
    assert mailer.with_ad_prefix("(광고) 세무 안내") == "(광고) 세무 안내"


def test_ad_prefix_handles_empty():
    assert mailer.with_ad_prefix("") == "(광고)"
    assert mailer.with_ad_prefix(None) == "(광고)"


def test_unsubscribe_notice_appended():
    out = mailer.with_unsubscribe("본문입니다.")
    assert out.startswith("본문입니다.")
    assert "수신거부" in out


def test_unsubscribe_handles_empty():
    assert "수신거부" in mailer.with_unsubscribe("")


# ── 발송 경로 (SMTP는 가짜로 대체) ────────────────────────────────────────
class _FakeSMTP:
    sent = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.tls = True

    def login(self, user, password):
        self.user = user

    def send_message(self, msg):
        _FakeSMTP.sent.append(msg)


def test_send_gmail_applies_legal_notices(monkeypatch):
    _FakeSMTP.sent.clear()
    monkeypatch.setattr(mailer.smtplib, "SMTP", _FakeSMTP)

    full_subject = mailer.send_gmail(
        "me@gmail.com", "apppassword", "boss@happy.co.kr",
        "세무 안내", "본문입니다.", "행복세무회계",
    )

    assert full_subject == "(광고) 세무 안내"
    msg = _FakeSMTP.sent[0]
    assert msg["Subject"] == "(광고) 세무 안내"
    assert msg["To"] == "boss@happy.co.kr"
    assert msg["From"] == "행복세무회계 <me@gmail.com>"
    assert "수신거부" in msg.get_content()


def test_send_gmail_without_sender_name(monkeypatch):
    _FakeSMTP.sent.clear()
    monkeypatch.setattr(mailer.smtplib, "SMTP", _FakeSMTP)
    mailer.send_gmail("me@gmail.com", "pw", "b@b.kr", "제목", "본문")
    assert _FakeSMTP.sent[0]["From"] == "me@gmail.com"
