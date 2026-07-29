"""데모 데이터 로딩과 데모 세션 상태 관리.

앱을 처음 열면 명단·이력이 비어 있어 기능을 이해하기 어렵다.
`demo/` 의 가상 데이터를 세션 메모리로 불러와 전체 흐름을 체험하게 한다.

설계 원칙
- 데모 데이터는 **세션 메모리(st.session_state)에만** 존재한다.
  `data/*.csv` 는 읽지도 쓰지도 않는다.
- 판정 로직은 새로 만들지 않고 `store` 의 순수 함수를 그대로 재사용한다.
  (`clean_rows`, `has_sent`, `is_valid_email`, `sanitize`)
  데모에서 본 동작이 실제 동작과 같다는 것을 보장하기 위해서다.
- 데모 모드에서는 SMTP를 호출하지 않는다. mailer 를 import 하지도 않는다.
"""
from __future__ import annotations

import csv
from pathlib import Path

import streamlit as st

import store

DEMO_DIR = Path(__file__).parent / "demo"
DEMO_SUBSCRIBERS_CSV = DEMO_DIR / "demo_구독자.csv"
DEMO_HISTORY_CSV = DEMO_DIR / "demo_발송이력.csv"

# session_state 키
MODE_KEY = "demo_mode"
SUBSCRIBERS_KEY = "demo_subscribers"
HISTORY_KEY = "demo_history"

BANNER = (
    "🧪 **DEMO MODE** — 현재 가상 데이터가 표시되고 있으며 "
    "실제 구독자 데이터에는 영향을 주지 않습니다."
)
INTRO = (
    "실제 개인정보가 아닌 가상 신청자 데이터로 명단 검증, 맞춤 문안, "
    "발송 대상 추출과 발송 이력 기능을 체험할 수 있습니다. "
    "example.com 주소는 실제 발송용 주소가 아닙니다."
)
SEND_DONE = "데모 발송이 완료되었습니다. 실제 이메일은 전송되지 않았습니다."


class DemoDataError(RuntimeError):
    """데모 CSV가 없거나 형식이 어긋날 때."""


# ── CSV 로딩 ──────────────────────────────────────────────────────────────
def _read_csv(path: Path, required: list[str]) -> list[dict]:
    if not path.exists():
        raise DemoDataError(
            f"데모 파일을 찾을 수 없습니다: {path.name}\n\n"
            f"저장소의 `demo/` 폴더에 `{path.name}` 이 있어야 합니다."
        )
    try:
        # utf-8-sig : Excel 이 붙이는 BOM 을 자동으로 걷어낸다.
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except UnicodeDecodeError as exc:
        raise DemoDataError(
            f"`{path.name}` 을 UTF-8 로 읽지 못했습니다. "
            "Excel에서 저장했다면 'CSV UTF-8' 형식으로 다시 저장해 주세요."
        ) from exc

    if not rows:
        raise DemoDataError(f"`{path.name}` 에 데이터 행이 없습니다.")

    missing = [c for c in required if c not in rows[0]]
    if missing:
        raise DemoDataError(
            f"`{path.name}` 의 컬럼이 맞지 않습니다. "
            f"빠진 컬럼: {', '.join(missing)}\n\n"
            f"필요한 컬럼: {', '.join(required)}"
        )
    # 실제 신청 저장과 같은 정리를 거친다. (개행·제어문자 제거, 앞뒤 공백 정리)
    return [{c: store.sanitize(r.get(c, "")) for c in required} for r in rows]


def load_demo_subscribers() -> list[dict]:
    """demo/demo_구독자.csv 를 읽어 구독자 목록으로 반환."""
    return _read_csv(DEMO_SUBSCRIBERS_CSV, store.SUBSCRIBER_FIELDS)


def load_demo_history() -> list[dict]:
    """demo/demo_발송이력.csv 를 읽어 발송 이력 목록으로 반환."""
    return _read_csv(DEMO_HISTORY_CSV, store.HISTORY_FIELDS)


# ── 세션 상태 ─────────────────────────────────────────────────────────────
def is_demo_mode() -> bool:
    return bool(st.session_state.get(MODE_KEY))


def start_demo() -> None:
    """데모 CSV를 세션으로 읽어 들이고 데모 모드를 켠다.

    파일 읽기가 먼저 성공해야 모드를 켜므로, 실패 시 실제 모드 그대로 남는다.
    """
    subscribers = load_demo_subscribers()
    history = load_demo_history()
    st.session_state[SUBSCRIBERS_KEY] = subscribers
    st.session_state[HISTORY_KEY] = history
    st.session_state[MODE_KEY] = True


def stop_demo() -> None:
    """데모 데이터를 버리고 실제 데이터 모드로 돌아간다.

    `data/*.csv` 는 읽기만 재개할 뿐 어떤 수정도 하지 않는다.
    """
    for key in (SUBSCRIBERS_KEY, HISTORY_KEY, MODE_KEY):
        st.session_state.pop(key, None)


# ── 데모 데이터 접근 (세션 메모리 전용) ───────────────────────────────────
def demo_subscribers() -> list[dict]:
    return st.session_state.get(SUBSCRIBERS_KEY, [])


def demo_history() -> list[dict]:
    return st.session_state.get(HISTORY_KEY, [])


def demo_delete_subscriber(email: str) -> None:
    target = (email or "").strip().lower()
    st.session_state[SUBSCRIBERS_KEY] = [
        r for r in demo_subscribers() if r.get("이메일", "").strip().lower() != target
    ]


def record_demo_send(email: str, company: str, ceo: str,
                     template_name: str, subject: str, sent_at: str) -> None:
    """데모 발송 이력 1건을 세션에 추가한다. 파일에는 쓰지 않는다."""
    st.session_state[HISTORY_KEY] = demo_history() + [
        {
            "이메일": email,
            "업체명": company,
            "대표자": ceo,
            "템플릿": template_name,
            "제목": subject,
            "발송일시": sent_at,
        }
    ]
