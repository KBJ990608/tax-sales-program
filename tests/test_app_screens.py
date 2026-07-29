"""앱 화면 통합 테스트 — Streamlit AppTest 로 실제 렌더링을 돌린다."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import mailer
import store

APP = str(Path(__file__).resolve().parents[1] / "app.py")
ADMIN_PAGES = ["② 명단 관리", "③ 메일 보내기", "④ 발송 이력"]
ADMIN_PAGES_ALL = ["① 신청받기"] + ADMIN_PAGES  # 사이드바 메뉴 전체


def run_app(page=None, *, admin=False):
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    if page:
        at.radio[0].set_value(page).run()
    if admin:
        at.session_state["_admin_ok"] = True
        at.run()
    return at


# ── 관리자 인증 (fail-closed) ─────────────────────────────────────────────
@pytest.mark.parametrize("page", ADMIN_PAGES)
def test_admin_pages_blocked_without_password(page):
    """비밀번호 미설정 시 관리 화면이 열리면 구독자 명단이 공개된다."""
    at = run_app(page)
    assert at.error, f"{page}: 차단 메시지가 없다"
    assert not any(page.strip("①②③④ ") in h.value for h in at.header)


@pytest.mark.parametrize("page", ADMIN_PAGES)
def test_admin_pages_open_with_correct_password(page, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    at = run_app(page, admin=True)
    assert not at.exception
    assert at.header


def test_wrong_password_does_not_unlock(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    at = run_app("② 명단 관리")
    at.text_input[0].set_value("wrong").run()
    at.button[0].click().run()
    assert at.error
    assert "_admin_ok" not in at.session_state


def test_correct_password_unlocks(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    at = run_app("② 명단 관리")
    at.text_input[0].set_value("s3cret").run()
    at.button[0].click().run()
    assert at.session_state["_admin_ok"] is True


def test_dev_mode_opens_admin_without_password(monkeypatch):
    monkeypatch.setenv("TAXMAILER_DEV", "1")
    at = run_app("② 명단 관리")
    assert not at.error
    assert any("명단 관리" in h.value for h in at.header)


# ── ① 신청받기 (공개) ─────────────────────────────────────────────────────
def test_landing_page_is_public():
    at = run_app()
    assert not at.exception
    assert not at.error


def test_apply_form_saves_subscriber():
    at = run_app()
    at.text_input[0].set_value("행복상사")
    at.text_input[1].set_value("홍길동")
    at.text_input[2].set_value("boss@happy.co.kr")
    at.checkbox[0].set_value(True)
    at.button[0].click().run()
    assert at.success
    assert len(store.load_subscribers()) == 1


def test_apply_form_rejects_without_consent():
    at = run_app()
    at.text_input[0].set_value("무동의상사")
    at.text_input[2].set_value("no@consent.kr")
    at.button[0].click().run()
    assert at.error
    assert store.load_subscribers() == []


# ── ③ 메일 보내기 ─────────────────────────────────────────────────────────
def test_send_button_disabled_until_confirmed(monkeypatch):
    """확인 체크 없이는 실제 발송 버튼이 눌리지 않아야 한다."""
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    store.add_subscriber("행복상사", "홍길동", "boss@happy.co.kr", True)

    at = run_app("③ 메일 보내기", admin=True)
    send = [b for b in at.button if "발송" in b.label]
    assert send, "발송 버튼을 찾지 못했다"
    assert send[0].disabled is True

    confirm = [c for c in at.checkbox if "실제로 발송" in c.label]
    assert confirm, "발송 확인 체크박스를 찾지 못했다"
    confirm[0].set_value(True).run()
    send = [b for b in at.button if "발송" in b.label]
    assert send[0].disabled is False


def test_send_requires_gmail_credentials(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    store.add_subscriber("행복상사", "홍길동", "boss@happy.co.kr", True)

    at = run_app("③ 메일 보내기", admin=True)
    [c for c in at.checkbox if "실제로 발송" in c.label][0].set_value(True).run()
    [b for b in at.button if "발송" in b.label][0].click().run()
    assert any("Gmail" in e.value for e in at.error)
    assert store.load_history() == []


def test_already_sent_recipients_are_excluded(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    store.add_subscriber("행복상사", "홍길동", "boss@happy.co.kr", True)
    store.record_send("boss@happy.co.kr", "행복상사", "홍길동", "환영", "(광고) 제목")

    at = run_app("③ 메일 보내기", admin=True)
    assert any("대상이 없습니다" in i.value for i in at.info)


def test_template_selectbox_lists_all_five(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    at = run_app("③ 메일 보내기", admin=True)
    assert len(at.selectbox[0].options) == 5


def test_ai_button_disabled_without_api_key(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    at = run_app("③ 메일 보내기", admin=True)
    mode = [r for r in at.radio if any("AI" in o for o in r.options)][0]
    mode.set_value("🤖 AI 맞춤 생성").run()
    assert at.warning
    ai_btn = [b for b in at.button if "AI로 문안 생성" in b.label]
    assert ai_btn[0].disabled is True


# ── ② 명단 관리 / ④ 발송 이력 ─────────────────────────────────────────────
def test_subscriber_table_flags_status(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    store.add_subscriber("A상사", "가", "a@a.kr", True)
    store.add_subscriber("B상사", "나", "b@b.kr", True)
    store.record_send("b@b.kr", "B상사", "나", "환영", "(광고) 제목")

    at = run_app("② 명단 관리", admin=True)
    assert not at.exception
    df = at.dataframe[0].value
    statuses = dict(zip(df["이메일"], df["상태"]))
    assert statuses["a@a.kr"] == "🟢 발송대기"
    assert statuses["b@b.kr"] == "✅ 발송완료"


def test_history_page_renders(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    store.record_send("a@a.kr", "A상사", "가", "환영", "(광고) 제목")
    at = run_app("④ 발송 이력", admin=True)
    assert not at.exception
    assert at.metric[-1].value == "1건"


def test_empty_states_render_without_error(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    for page in ADMIN_PAGES:
        at = run_app(page, admin=True)
        assert not at.exception, f"{page} 에서 예외 발생"


# ── 데모 모드 (화면 통합) ─────────────────────────────────────────────────
def run_demo(page, monkeypatch):
    """데모 모드를 켠 채로 원하는 화면을 연다."""
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["_admin_ok"] = True
    at.run()
    at.radio[0].set_value("② 명단 관리").run()
    [b for b in at.button if b.label == "데모 데이터 불러오기"][0].click().run()
    if page != "② 명단 관리":
        at.radio[0].set_value(page).run()
    return at


def test_demo_button_present_and_loads(monkeypatch):
    at = run_demo("② 명단 관리", monkeypatch)
    assert not at.exception
    assert at.session_state["demo_mode"] is True
    assert len(at.session_state["demo_subscribers"]) >= 10


def test_demo_banner_shown_on_admin_pages(monkeypatch):
    for page in ADMIN_PAGES:
        at = run_demo(page, monkeypatch)
        assert any("DEMO MODE" in i.value for i in at.info), page


def test_demo_not_loaded_without_button_click(monkeypatch):
    """명시적으로 버튼을 눌러야만 데모가 켜진다."""
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    at = run_app("② 명단 관리", admin=True)
    assert "demo_mode" not in at.session_state
    assert not any("DEMO MODE" in i.value for i in at.info)


def test_demo_table_shows_all_statuses(monkeypatch):
    at = run_demo("② 명단 관리", monkeypatch)
    statuses = set(at.dataframe[0].value["상태"])
    assert statuses == {"🟢 발송대기", "✅ 발송완료", "⚠️ 중복", "❌ 잘못된 이메일"}


def test_demo_html_value_is_escaped_not_executed(monkeypatch):
    """<script> 가 마크다운/HTML 로 렌더되지 않고 표 안의 글자로만 존재해야 한다."""
    at = run_demo("② 명단 관리", monkeypatch)
    payload = "<script>alert('demo')</script>"
    assert payload in list(at.dataframe[0].value["대표자"])  # 표에는 글자로 존재
    for el in list(at.markdown) + list(at.info) + list(at.warning) + list(at.error):
        assert payload not in el.value  # 마크다운 경로에는 절대 없어야 한다


def test_demo_history_page_shows_seeded_rows(monkeypatch):
    at = run_demo("④ 발송 이력", monkeypatch)
    df = at.dataframe[0].value
    assert len(df) == 3
    assert set(df["템플릿"]) == {"개업축하", "환영", "기장대행"}


def test_demo_send_screen_hides_gmail_inputs(monkeypatch):
    at = run_demo("③ 메일 보내기", monkeypatch)
    labels = [t.label for t in at.text_input]
    assert "Gmail 앱 비밀번호" not in labels
    assert "발신 Gmail 주소" not in labels


def test_demo_send_button_is_relabelled_and_gated(monkeypatch):
    at = run_demo("③ 메일 보내기", monkeypatch)
    send = [b for b in at.button if "데모 발송 실행" in b.label]
    assert send, [b.label for b in at.button]
    assert send[0].disabled is True
    assert not any("바로 발송" in b.label for b in at.button)


def test_demo_send_simulates_without_smtp(monkeypatch):
    """데모 발송이 SMTP 를 호출하지 않고 세션 이력만 늘린다."""
    import smtplib

    def _boom(*a, **k):
        raise AssertionError("데모 모드에서 SMTP 가 호출되었다")

    monkeypatch.setattr(smtplib, "SMTP", _boom)
    monkeypatch.setattr(mailer, "send_gmail", _boom)

    at = run_demo("③ 메일 보내기", monkeypatch)
    before = len(at.session_state["demo_history"])
    n_candidates = len(at.dataframe[0].value)

    [c for c in at.checkbox if "시뮬레이션" in c.label][0].set_value(True).run()
    [b for b in at.button if "데모 발송 실행" in b.label][0].click().run()

    assert not at.exception
    assert any("실제 이메일은 전송되지 않았습니다" in s.value for s in at.success)
    assert len(at.session_state["demo_history"]) == before + n_candidates
    assert store.load_history() == []  # 실제 이력 파일은 그대로


def test_demo_send_then_resend_blocked(monkeypatch):
    at = run_demo("③ 메일 보내기", monkeypatch)
    [c for c in at.checkbox if "시뮬레이션" in c.label][0].set_value(True).run()
    [b for b in at.button if "데모 발송 실행" in b.label][0].click().run()
    # 같은 템플릿(환영)으로 다시 오면 대상이 없어야 한다
    assert any("대상이 없습니다" in i.value for i in at.info)


def test_demo_panel_shows_only_stop_button(monkeypatch):
    """데모 중에는 '데모 종료' 하나만 두고, 재설정·사용 방법은 두지 않는다."""
    at = run_demo("② 명단 관리", monkeypatch)
    labels = [b.label for b in at.button]
    assert "데모 종료" in labels
    assert "데모 초기 상태로 재설정" not in labels
    assert "데모 데이터 불러오기" not in labels
    assert not any("데모 사용 방법" in e.label for e in at.expander)


def test_demo_stop_returns_to_real_data(monkeypatch):
    at = run_demo("② 명단 관리", monkeypatch)
    [b for b in at.button if b.label == "데모 종료"][0].click().run()
    assert "demo_mode" not in at.session_state
    assert not any("DEMO MODE" in i.value for i in at.info)
    assert store.load_subscribers() == []  # 실제 데이터는 여전히 비어 있음


def test_demo_delete_does_not_touch_real_file(monkeypatch):
    store.add_subscriber("실제상사", "진짜", "real@company.co.kr", True)
    at = run_demo("② 명단 관리", monkeypatch)
    at.selectbox[0].set_value("bom@example.com").run()
    [b for b in at.button if b.label == "삭제"][0].click().run()
    assert [r["이메일"] for r in store.load_subscribers()] == ["real@company.co.kr"]


def test_real_mode_send_flow_unchanged(monkeypatch):
    """데모 기능 추가 후에도 실제 발송 흐름은 그대로여야 한다."""
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    store.add_subscriber("행복상사", "홍길동", "boss@happy.co.kr", True)

    at = run_app("③ 메일 보내기", admin=True)
    labels = [t.label for t in at.text_input]
    assert "발신 Gmail 주소" in labels and "Gmail 앱 비밀번호" in labels
    send = [b for b in at.button if "바로 발송" in b.label]
    assert send and send[0].disabled is True

    [c for c in at.checkbox if "실제로 발송" in c.label][0].set_value(True).run()
    [b for b in at.button if "바로 발송" in b.label][0].click().run()
    assert any("Gmail" in e.value for e in at.error)


def test_public_apply_page_unaffected_by_demo(monkeypatch):
    at = run_demo("② 명단 관리", monkeypatch)
    at.radio[0].set_value("① 신청받기").run()
    assert not at.exception
    assert not any("DEMO MODE" in i.value for i in at.info)  # 공개 화면엔 배너 없음
    at.text_input[0].set_value("실제상사")
    at.text_input[2].set_value("real@company.co.kr")
    at.checkbox[0].set_value(True)
    at.button[0].click().run()
    assert at.success
    assert [r["이메일"] for r in store.load_subscribers()] == ["real@company.co.kr"]
