"""AI 문안 생성 테스트 (ai.py). 네트워크를 타지 않는다."""
import ai


def test_placeholders_are_literal_constants():
    """f-string 안에 중괄호를 그대로 쓰면 NameError 가 났던 회귀 버그 방어."""
    assert ai.COMPANY_PLACEHOLDER == "{업체명}"
    assert ai.CEO_PLACEHOLDER == "{대표자}"


def test_generate_template_builds_prompt_without_nameerror(monkeypatch):
    """프롬프트 조립 단계에서 터지지 않고 API 호출까지 도달해야 한다."""
    captured = {}

    class _FakeMessages:
        def parse(self, **kwargs):
            captured.update(kwargs)
            return type("R", (), {"parsed_output": ai.EmailDraft(subject="제목", body="본문")})()

    class _FakeClient:
        messages = _FakeMessages()

    monkeypatch.setattr(ai.anthropic, "Anthropic", lambda **kw: _FakeClient())
    monkeypatch.setattr(ai, "api_key", lambda: "sk-ant-test")

    subject, body = ai.generate_template("기장대행 상담 제안", "담백하게")

    assert (subject, body) == ("제목", "본문")
    prompt = captured["messages"][0]["content"]
    assert "{업체명}" in prompt
    assert "{대표자}" in prompt
    assert "기장대행 상담 제안" in prompt
    assert "담백하게" in prompt


def test_generate_template_uses_configured_model(monkeypatch):
    captured = {}

    class _FakeMessages:
        def parse(self, **kwargs):
            captured.update(kwargs)
            return type("R", (), {"parsed_output": ai.EmailDraft(subject="s", body="b")})()

    monkeypatch.setattr(
        ai.anthropic, "Anthropic", lambda **kw: type("C", (), {"messages": _FakeMessages()})()
    )
    monkeypatch.setattr(ai, "api_key", lambda: "sk-ant-test")
    ai.generate_template("", "")
    assert captured["model"] == ai.MODEL


def test_generate_template_raises_when_parse_returns_none(monkeypatch):
    class _FakeMessages:
        def parse(self, **kwargs):
            return type("R", (), {"parsed_output": None})()

    monkeypatch.setattr(
        ai.anthropic, "Anthropic", lambda **kw: type("C", (), {"messages": _FakeMessages()})()
    )
    monkeypatch.setattr(ai, "api_key", lambda: "sk-ant-test")
    try:
        ai.generate_template("brief", "tone")
    except RuntimeError as exc:
        assert "문안" in str(exc)
    else:
        raise AssertionError("parsed_output 이 None 이면 예외를 던져야 한다")


def test_has_key_false_without_configuration():
    assert ai.has_key() is False


def test_has_key_true_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert ai.has_key() is True


def test_system_prompt_forbids_ad_prefix_and_unsubscribe():
    """(광고)·수신거부는 mailer가 붙이므로 AI가 넣으면 중복된다."""
    assert "(광고)" in ai.SYSTEM
    assert "수신거부" in ai.SYSTEM
