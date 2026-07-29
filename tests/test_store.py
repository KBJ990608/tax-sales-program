"""구독자 저장·검증 로직 테스트 (store.py)."""
import store


# ── 이메일 검증 ───────────────────────────────────────────────────────────
def test_valid_email_forms():
    assert store.is_valid_email("boss@happy.co.kr")
    assert store.is_valid_email("a.b+tag@sub.example.com")


def test_invalid_email_forms():
    for bad in ["", "boss", "boss@", "@happy.kr", "boss@happy", "a b@c.kr", None]:
        assert not store.is_valid_email(bad), bad


# ── 헤더 인젝션 방어 ──────────────────────────────────────────────────────
def test_sanitize_strips_newlines():
    """개행이 남으면 메일 헤더에 Bcc 등을 주입할 수 있다."""
    dirty = "행복상사\r\nBcc: attacker@evil.com"
    clean = store.sanitize(dirty)
    assert "\n" not in clean and "\r" not in clean


def test_sanitize_strips_control_chars_and_limits_length():
    assert "\x00" not in store.sanitize("행복\x00상사")
    assert len(store.sanitize("가" * 500)) == 200
    assert len(store.sanitize("가" * 500, limit=50)) == 50


def test_sanitize_keeps_tab_and_trims():
    assert store.sanitize("  행복상사  ") == "행복상사"


# ── 구독자 추가 ───────────────────────────────────────────────────────────
def test_add_subscriber_success():
    ok, msg = store.add_subscriber("행복상사", "홍길동", "boss@happy.co.kr", True)
    assert ok
    assert "행복상사" in msg
    rows = store.load_subscribers()
    assert len(rows) == 1
    assert rows[0]["이메일"] == "boss@happy.co.kr"
    assert rows[0]["수신동의"] == "동의"
    assert rows[0]["신청일시"]


def test_add_subscriber_requires_consent():
    """수신 동의 없이는 저장되지 않아야 한다 — 합법성의 핵심."""
    ok, msg = store.add_subscriber("무동의상사", "홍길동", "no@consent.kr", False)
    assert not ok
    assert "동의" in msg
    assert store.load_subscribers() == []


def test_add_subscriber_requires_company():
    ok, _ = store.add_subscriber("", "홍길동", "a@b.kr", True)
    assert not ok


def test_add_subscriber_rejects_bad_email():
    ok, msg = store.add_subscriber("행복상사", "홍길동", "not-an-email", True)
    assert not ok
    assert "이메일" in msg


def test_add_subscriber_rejects_duplicate():
    assert store.add_subscriber("행복상사", "홍길동", "boss@happy.co.kr", True)[0]
    ok, msg = store.add_subscriber("다른상사", "김철수", "boss@happy.co.kr", True)
    assert not ok
    assert "이미" in msg
    assert len(store.load_subscribers()) == 1


def test_add_subscriber_sanitizes_input():
    store.add_subscriber("행복상사\r\nBcc: evil@x.com", "홍길동", "boss@happy.co.kr", True)
    saved = store.load_subscribers()[0]["업체명"]
    assert "\n" not in saved and "\r" not in saved


# ── 삭제·정리 ─────────────────────────────────────────────────────────────
def test_delete_subscriber():
    store.add_subscriber("A상사", "가", "a@a.kr", True)
    store.add_subscriber("B상사", "나", "b@b.kr", True)
    store.delete_subscriber("a@a.kr")
    assert [r["이메일"] for r in store.load_subscribers()] == ["b@b.kr"]


def test_delete_subscriber_is_case_insensitive():
    store.add_subscriber("A상사", "가", "a@a.kr", True)
    store.delete_subscriber("A@A.KR")
    assert store.load_subscribers() == []


def test_clean_subscribers_filters_invalid_and_duplicates():
    """CSV를 손으로 고친 경우까지 대비 — clean_subscribers 가 최종 방어선."""
    store.add_subscriber("A상사", "가", "a@a.kr", True)
    with store.SUBSCRIBERS_CSV.open("a", encoding="utf-8-sig", newline="") as f:
        f.write("깨진상사,나,broken-email,동의,2026-01-01 00:00:00\n")
        f.write("중복상사,다,A@A.KR,동의,2026-01-01 00:00:00\n")
    assert len(store.load_subscribers()) == 3
    cleaned = store.clean_subscribers()
    assert [r["이메일"] for r in cleaned] == ["a@a.kr"]


# ── 발송 이력 ─────────────────────────────────────────────────────────────
def test_record_and_check_already_sent():
    store.record_send("a@a.kr", "A상사", "가", "환영", "(광고) 제목")
    assert store.already_sent("a@a.kr", "환영")
    assert not store.already_sent("a@a.kr", "기장대행")
    assert not store.already_sent("b@b.kr", "환영")


def test_already_sent_is_case_insensitive():
    store.record_send("a@a.kr", "A상사", "가", "환영", "(광고) 제목")
    assert store.already_sent("A@A.KR", "환영")


def test_load_history_returns_recorded_fields():
    store.record_send("a@a.kr", "A상사", "가", "환영", "(광고) 제목")
    row = store.load_history()[0]
    assert row["업체명"] == "A상사"
    assert row["템플릿"] == "환영"
    assert row["제목"] == "(광고) 제목"
    assert row["발송일시"]


# ── 파일이 없는 상태에서의 첫 호출 ────────────────────────────────────────
def test_loads_return_empty_when_no_file_yet():
    assert store.load_subscribers() == []
    assert store.load_history() == []


def test_creates_data_dir_when_missing(tmp_path, monkeypatch):
    """배포 환경에서 data/ 가 없어도 첫 저장이 성공해야 한다."""
    nested = tmp_path / "없는" / "깊은" / "경로"
    monkeypatch.setattr(store, "DATA_DIR", nested)
    monkeypatch.setattr(store, "SUBSCRIBERS_CSV", nested / "구독자.csv")
    assert store.add_subscriber("행복상사", "홍길동", "boss@happy.co.kr", True)[0]
    assert (nested / "구독자.csv").exists()
