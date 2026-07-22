"""Claude(Anthropic) API로 세무 영업 메일 문안을 생성한다.

- 짧은 브리프(목적/톤)를 받아 {업체명}·{대표자} 플레이스홀더가 들어간
  재사용 가능한 템플릿(제목+본문)을 한 번의 호출로 생성한다.
- (광고) 접두와 수신거부 문구는 mailer가 자동으로 붙이므로 여기서는 넣지 않는다.
- API 키는 secrets(anthropic_api_key) 또는 환경변수 ANTHROPIC_API_KEY에서 읽는다.
"""
from __future__ import annotations

import os

import anthropic
import streamlit as st
from pydantic import BaseModel

MODEL = "claude-opus-4-8"


class EmailDraft(BaseModel):
    subject: str
    body: str


def api_key() -> str | None:
    try:
        if "anthropic_api_key" in st.secrets:
            return str(st.secrets["anthropic_api_key"])
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def has_key() -> bool:
    return bool(api_key())


SYSTEM = """너는 한국 세무사·세무회계 사무소의 영업 담당자다.
세무 정보를 받겠다고 직접 신청한(수신 동의한) 사장님들에게 보낼 맞춤 영업 이메일 문안을 작성한다.

규칙:
- 제목과 본문에 반드시 리터럴 플레이스홀더 {업체명} 와 {대표자} 를 사용한다. (실제 이름을 넣지 말고 중괄호 그대로)
- 정중하고 신뢰감 있는 한국어. 과장·허위(환급률/절세율/1위/최고 등) 표현 금지.
- 본문은 3~5문단, 각 문단 짧게. 마지막은 회신 유도로 마무리.
- 제목에 (광고) 표기나 수신거부 안내는 넣지 마라. (시스템이 자동으로 붙인다)
"""


def generate_template(brief: str, tone: str) -> tuple[str, str]:
    """브리프+톤으로 (제목, 본문) 템플릿을 생성. 실패 시 예외를 던진다."""
    client = anthropic.Anthropic(api_key=api_key())
    user = f"""다음 조건으로 영업 메일 템플릿을 작성해줘.

목적/내용: {brief.strip() or "세무 정보 신청 감사 및 상담 제안"}
톤: {tone.strip() or "정중하고 담백하게"}

{업체명} 와 {대표자} 플레이스홀더를 반드시 포함해줘."""

    response = client.messages.parse(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
        output_format=EmailDraft,
    )
    draft = response.parsed_output
    if draft is None:
        raise RuntimeError("AI가 형식에 맞는 문안을 만들지 못했습니다. 다시 시도해 주세요.")
    return draft.subject, draft.body
