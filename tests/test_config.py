"""설정(secrets)·배포 파일이 실제 코드와 어긋나지 않는지 검증한다.

예시 파일과 코드가 따로 놀면 "README대로 했는데 안 된다"가 생기므로
키 목록을 코드에서 뽑아 예시 파일과 대조한다.
"""
import re
import tomllib
from pathlib import Path

import ai
import auth

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".streamlit" / "secrets.toml.example"
README = ROOT / "README.md"

# 코드가 st.secrets 에서 읽는 키 (auth.py / ai.py / app.py 의 secret() 호출)
CODE_KEYS = {
    "admin_password",       # auth.py
    "anthropic_api_key",    # ai.py
    "gmail_address",        # app.py secret()
    "gmail_app_password",   # app.py secret()
    "sender_name",          # app.py secret()
}


def _example_keys() -> set[str]:
    """예시 파일에서 주석이 아닌 실제 키만 뽑는다."""
    return set(tomllib.loads(EXAMPLE.read_text(encoding="utf-8")).keys())


def test_example_file_is_valid_toml():
    tomllib.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_covers_every_key_the_code_reads():
    missing = CODE_KEYS - _example_keys()
    assert not missing, f"예시 파일에 빠진 키: {missing}"


def test_example_has_no_unknown_keys():
    extra = _example_keys() - CODE_KEYS
    assert not extra, f"코드가 읽지 않는 키가 예시에 있음: {extra}"


def test_app_reads_the_same_keys_as_documented():
    """app.py 의 secret("...") 호출 인자가 CODE_KEYS 안에 있는지."""
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    called = set(re.findall(r'secret\("([a-z_]+)"', src))
    assert called <= CODE_KEYS, f"문서화되지 않은 키를 읽고 있음: {called - CODE_KEYS}"


def test_example_contains_no_real_secret():
    """예시 파일에 진짜 키·비밀번호가 들어가지 않게 막는다."""
    text = EXAMPLE.read_text(encoding="utf-8")
    assert "sk-ant-api" not in text
    parsed = tomllib.loads(text)
    assert parsed["anthropic_api_key"] == "", "예시의 API 키는 비어 있어야 한다"
    assert parsed["admin_password"] == "CHANGE_ME", "예시 비밀번호는 자리표시자여야 한다"
    # 발신 계정 정보도 비어 있어야 한다
    for k in ("gmail_address", "gmail_app_password", "sender_name"):
        assert parsed[k] == "", f"{k} 는 비어 있어야 한다"


# ── 값이 비어 있을 때의 안전한 동작 ──────────────────────────────────────
def test_empty_anthropic_key_disables_ai_without_crashing(monkeypatch):
    """키가 빈 문자열이어도 앱이 죽지 않고 AI 기능만 비활성화된다."""
    monkeypatch.setattr(ai, "api_key", lambda: "")
    assert ai.has_key() is False


def test_missing_anthropic_key_is_falsy():
    assert ai.has_key() is False  # conftest 가 환경변수를 지운 상태


def test_placeholder_admin_password_still_locks_admin(monkeypatch):
    """CHANGE_ME 라도 비밀번호가 설정된 것이므로 로그인 폼이 떠야 한다."""
    monkeypatch.setenv("ADMIN_PASSWORD", "CHANGE_ME")
    assert auth._configured_password() == "CHANGE_ME"


def test_no_admin_password_means_fail_closed(monkeypatch):
    assert auth._configured_password() is None
    assert auth._dev_mode() is False


def test_dev_mode_only_via_explicit_env(monkeypatch):
    for value in ("1", "true", "TRUE", "yes"):
        monkeypatch.setenv("TAXMAILER_DEV", value)
        assert auth._dev_mode() is True
    for value in ("", "0", "false", "no", "아무거나"):
        monkeypatch.setenv("TAXMAILER_DEV", value)
        assert auth._dev_mode() is False


# ── 배포 파일 ────────────────────────────────────────────────────────────
def test_requirements_pins_versions_actually_used():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit>=1.49" in req   # width="stretch"
    assert "anthropic>=0.120" in req  # messages.parse(output_format=)
    assert "pytest" not in req, "테스트 의존성은 requirements-dev.txt 로 분리한다"


def test_dev_requirements_include_base():
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" in dev
    assert "pytest" in dev


def test_gitignore_excludes_real_data_but_not_demo():
    # 주석을 뺀 실제 규칙만 본다. (주석에 'demo' 가 나올 수 있다)
    rules = [
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert "data/*.csv" in rules
    assert ".streamlit/secrets.toml" in rules
    assert not [r for r in rules if "demo" in r], "데모 예시는 저장소에 포함되어야 한다"


# ── README 가 실제 구현과 일치하는지 ─────────────────────────────────────
def test_readme_documents_every_secret_key():
    text = README.read_text(encoding="utf-8")
    for key in CODE_KEYS:
        assert key in text, f"README 에 {key} 설명이 없음"


def test_readme_has_live_app_link():
    text = README.read_text(encoding="utf-8")
    assert "streamlit.app" in text


def test_readme_does_not_promise_removed_features():
    """구현에서 없앤 기능이 README 에 남아 있으면 안 된다."""
    text = README.read_text(encoding="utf-8")
    assert "데모 초기 상태로 재설정" not in text
    assert "데모 사용 방법" not in text
