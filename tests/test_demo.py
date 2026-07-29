"""데모 데이터·데모 모드 테스트 (demo.py).

핵심 안전 요건 두 가지를 집중적으로 검증한다.
  1) 데모 모드가 실제 data/*.csv 를 절대 건드리지 않는다.
  2) 데모 발송이 SMTP 를 절대 호출하지 않는다.
"""
from pathlib import Path

import pytest

import demo
import mailer
import store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def session(monkeypatch):
    """st.session_state 를 평범한 dict 로 대체해 Streamlit 없이 테스트한다."""
    state: dict = {}
    monkeypatch.setattr(demo.st, "session_state", state)
    return state


# ── CSV 로딩 ──────────────────────────────────────────────────────────────
def test_demo_files_exist_in_repo():
    assert demo.DEMO_SUBSCRIBERS_CSV.exists()
    assert demo.DEMO_HISTORY_CSV.exists()


def test_demo_files_are_utf8_bom():
    """Excel에서 한글이 깨지지 않도록 BOM이 있어야 한다."""
    for path in (demo.DEMO_SUBSCRIBERS_CSV, demo.DEMO_HISTORY_CSV):
        assert path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name


def test_load_demo_subscribers_matches_real_schema():
    rows = demo.load_demo_subscribers()
    assert len(rows) >= 10
    assert list(rows[0].keys()) == store.SUBSCRIBER_FIELDS


def test_load_demo_history_matches_real_schema():
    rows = demo.load_demo_history()
    assert len(rows) >= 3
    assert list(rows[0].keys()) == store.HISTORY_FIELDS


def test_demo_emails_are_example_com_or_intentionally_invalid():
    """실제 주소로 발송될 가능성이 없어야 한다."""
    for r in demo.load_demo_subscribers():
        email = r["이메일"]
        if store.is_valid_email(email):
            assert email.endswith("@example.com"), email
    for r in demo.load_demo_history():
        assert r["이메일"].endswith("@example.com"), r["이메일"]


def test_demo_dates_are_fixed():
    """실행할 때마다 결과가 달라지지 않도록 고정 날짜여야 한다."""
    assert demo.load_demo_subscribers()[0]["신청일시"] == "2026-07-20 09:12:00"
    assert demo.load_demo_history()[0]["발송일시"] == "2026-07-25 10:30:00"


# ── 모든 상태가 재현되는지 ────────────────────────────────────────────────
def _statuses():
    subs = demo.load_demo_subscribers()
    sent = {h["이메일"].strip().lower() for h in demo.load_demo_history()}
    seen: set[str] = set()
    out = []
    for r in subs:
        key = r["이메일"].strip().lower()
        if not store.is_valid_email(r["이메일"]):
            out.append("잘못된 이메일")
        elif key in seen:
            out.append("중복")
        elif key in sent:
            out.append("발송완료")
        else:
            out.append("발송대기")
        seen.add(key)
    return out


def test_demo_covers_every_status():
    s = _statuses()
    assert s.count("발송대기") >= 5
    assert s.count("중복") == 1          # 같은 이메일 2건 중 두 번째가 중복 처리
    assert s.count("잘못된 이메일") == 2
    assert s.count("발송완료") >= 2


def test_demo_has_duplicate_email_pair():
    emails = [r["이메일"].strip().lower() for r in demo.load_demo_subscribers()]
    assert emails.count("duplicate@example.com") == 2


def test_demo_whitespace_row_is_trimmed_on_load():
    """앞뒤 공백이 있는 원본이 sanitize 를 거쳐 정리된다."""
    raw = demo.DEMO_SUBSCRIBERS_CSV.read_text(encoding="utf-8-sig")
    assert "  공백테스트  " in raw  # 원본 CSV에는 공백이 있고
    loaded = {r["이메일"]: r for r in demo.load_demo_subscribers()}
    assert loaded["space@example.com"]["업체명"] == "공백테스트"  # 로드 후엔 정리됨
    assert loaded["space@example.com"]["대표자"] == "윤공백"


def test_demo_html_row_stays_literal_text():
    """HTML 이 실행되지 않고 글자 그대로 남아야 한다. (Streamlit이 이스케이프)"""
    loaded = {r["이메일"]: r for r in demo.load_demo_subscribers()}
    row = loaded["sanitize@example.com"]
    assert row["업체명"] == "<b>안전테스트</b>"
    assert row["대표자"] == "<script>alert('demo')</script>"
    # 개행·제어문자는 제거되어 메일 헤더 인젝션으로는 쓸 수 없다.
    assert "\n" not in row["대표자"] and "\r" not in row["대표자"]


# ── 세션 상태 ─────────────────────────────────────────────────────────────
def test_demo_mode_off_by_default(session):
    assert demo.is_demo_mode() is False


def test_start_demo_populates_session(session):
    demo.start_demo()
    assert demo.is_demo_mode() is True
    assert len(demo.demo_subscribers()) >= 10
    assert len(demo.demo_history()) >= 3


def test_stop_demo_clears_session(session):
    demo.start_demo()
    demo.stop_demo()
    assert demo.is_demo_mode() is False
    assert demo.demo_subscribers() == []
    assert demo.demo_history() == []


def test_restart_demo_restores_original_state(session):
    """데모를 다시 불러오면 원본 CSV 상태로 되돌아간다."""
    demo.start_demo()
    original_subs = len(demo.demo_subscribers())
    original_hist = len(demo.demo_history())

    demo.demo_delete_subscriber("bom@example.com")
    demo.record_demo_send("daon@example.com", "다온스튜디오", "최다온", "환영",
                          "(광고) 제목", "2026-07-28 00:00:00")
    assert len(demo.demo_subscribers()) == original_subs - 1
    assert len(demo.demo_history()) == original_hist + 1

    demo.start_demo()
    assert len(demo.demo_subscribers()) == original_subs
    assert len(demo.demo_history()) == original_hist


def test_start_demo_fails_cleanly_when_file_missing(session, monkeypatch, tmp_path):
    monkeypatch.setattr(demo, "DEMO_SUBSCRIBERS_CSV", tmp_path / "없음.csv")
    with pytest.raises(demo.DemoDataError) as exc:
        demo.start_demo()
    assert "찾을 수 없습니다" in str(exc.value)
    assert demo.is_demo_mode() is False  # 실패 시 실제 모드 유지


def test_start_demo_fails_cleanly_on_wrong_columns(session, monkeypatch, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("이름,메일\n홍길동,a@example.com\n", encoding="utf-8-sig")
    monkeypatch.setattr(demo, "DEMO_SUBSCRIBERS_CSV", bad)
    with pytest.raises(demo.DemoDataError) as exc:
        demo.start_demo()
    assert "컬럼이 맞지 않습니다" in str(exc.value)
    assert demo.is_demo_mode() is False


# ── 실제 데이터 격리 ──────────────────────────────────────────────────────
def test_demo_does_not_touch_real_csv(session, isolated_data):
    """데모를 켜고 조작해도 실제 data/*.csv 는 생성/변경되지 않는다."""
    store.add_subscriber("실제상사", "진짜", "real@company.co.kr", True)
    before_subs = store.SUBSCRIBERS_CSV.read_bytes()
    hist_existed = store.HISTORY_CSV.exists()

    demo.start_demo()
    demo.demo_delete_subscriber("bom@example.com")
    demo.record_demo_send("daon@example.com", "다온스튜디오", "최다온", "환영",
                          "(광고) 제목", "2026-07-28 00:00:00")
    demo.start_demo()
    demo.stop_demo()

    assert store.SUBSCRIBERS_CSV.read_bytes() == before_subs
    assert store.HISTORY_CSV.exists() == hist_existed
    assert [r["이메일"] for r in store.load_subscribers()] == ["real@company.co.kr"]


def test_demo_and_real_data_never_merge(session, isolated_data):
    store.add_subscriber("실제상사", "진짜", "real@company.co.kr", True)
    demo.start_demo()
    demo_emails = {r["이메일"] for r in demo.demo_subscribers()}
    assert "real@company.co.kr" not in demo_emails
    assert all(e not in {r["이메일"] for r in store.load_subscribers()}
               for e in demo_emails)


# ── 데모 발송: SMTP 미호출 ────────────────────────────────────────────────
def test_demo_module_does_not_import_mailer():
    """demo.py 는 SMTP 모듈을 아예 참조하지 않는다."""
    src = demo.__file__
    text = Path(src).read_text(encoding="utf-8")
    assert "import mailer" not in text
    assert "smtplib" not in text


def test_demo_send_does_not_call_smtp(session, monkeypatch):
    """데모 발송 경로에서 SMTP 가 호출되면 즉시 실패시킨다."""
    calls = []

    def _boom(*args, **kwargs):
        calls.append(args)
        raise AssertionError("데모 모드에서 SMTP 가 호출되었다")

    monkeypatch.setattr(mailer, "send_gmail", _boom)
    monkeypatch.setattr(mailer.smtplib, "SMTP", _boom)

    demo.start_demo()
    for r in store.clean_rows(demo.demo_subscribers()):
        demo.record_demo_send(r["이메일"], r["업체명"], r["대표자"], "환영",
                              "(광고) 제목", "2026-07-28 00:00:00")
    assert calls == []


def test_demo_send_only_grows_session_history(session, isolated_data):
    demo.start_demo()
    before = len(demo.demo_history())
    demo.record_demo_send("daon@example.com", "다온스튜디오", "최다온", "환영",
                          "(광고) 제목", "2026-07-28 00:00:00")
    assert len(demo.demo_history()) == before + 1
    assert store.load_history() == []  # 실제 이력은 그대로 비어 있음


def test_demo_resend_blocked_for_same_campaign(session):
    demo.start_demo()
    assert not store.has_sent(demo.demo_history(), "daon@example.com", "환영")
    demo.record_demo_send("daon@example.com", "다온스튜디오", "최다온", "환영",
                          "(광고) 제목", "2026-07-28 00:00:00")
    assert store.has_sent(demo.demo_history(), "daon@example.com", "환영")
    # 다른 캠페인은 여전히 대상
    assert not store.has_sent(demo.demo_history(), "daon@example.com", "기장대행")


def test_demo_history_seed_blocks_matching_campaigns(session):
    demo.start_demo()
    hist = demo.demo_history()
    assert store.has_sent(hist, "sent@example.com", "개업축하")
    assert store.has_sent(hist, "haneul@example.com", "환영")
    assert store.has_sent(hist, "onyu@example.com", "기장대행")
    # 캠페인이 다르면 차단되지 않는다
    assert not store.has_sent(hist, "sent@example.com", "환영")


def test_demo_history_templates_are_real_template_names():
    import templates
    valid = set(templates.template_names())
    for r in demo.load_demo_history():
        assert r["템플릿"] in valid, r["템플릿"]
