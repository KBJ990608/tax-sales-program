"""관리자 화면 접근을 비밀번호로 잠근다.

- 배포(공개) 시 아무나 명단·발송·이력에 접근하면 안 되므로 관리자 로그인을 요구한다.
- 비밀번호는 코드에 하드코딩하지 않는다:
    로컬:  .streamlit/secrets.toml 의 admin_password  또는 환경변수 ADMIN_PASSWORD
    배포:  Streamlit Cloud → App settings → Secrets 에 admin_password 설정
- 비밀번호는 상수시간 비교(hmac.compare_digest)로 확인한다.
"""
from __future__ import annotations

import hmac
import os

import streamlit as st


def _configured_password() -> str | None:
    # Streamlit secrets 우선, 없으면 환경변수
    try:
        if "admin_password" in st.secrets:
            return str(st.secrets["admin_password"])
    except Exception:  # secrets.toml 자체가 없을 때
        pass
    return os.environ.get("ADMIN_PASSWORD")


def _dev_mode() -> bool:
    """로컬 개발 전용 우회. 환경변수를 직접 켠 경우에만 참."""
    return os.environ.get("TAXMAILER_DEV", "").strip().lower() in {"1", "true", "yes"}


def require_admin() -> bool:
    """관리자 인증 통과 시 True. 아니면 로그인 폼을 그리고 False.

    비밀번호가 설정돼 있지 않으면 관리 화면을 막는다(fail-closed).
    구독자 명단은 개인정보이고 이 앱은 공개 배포될 수 있으므로, 설정 누락이
    곧 명단 공개로 이어지지 않도록 통과시키지 않는다.
    로컬 개발에서는 TAXMAILER_DEV=1 로 명시적으로 우회한다.
    """
    password = _configured_password()

    if not password:
        if _dev_mode():
            # 개발자가 직접 켠 우회 모드라 화면에 배너를 띄우지 않는다.
            return True
        st.error("🔒 관리자 비밀번호가 설정되지 않아 관리 화면을 열 수 없습니다.")
        st.markdown(
            "구독자 명단·발송 이력은 개인정보이므로 비밀번호 없이 공개하지 않습니다.\n\n"
            "**로컬에서 설정하기** — `.streamlit/secrets.toml` 에 다음을 추가한 뒤 앱을 재시작하세요.\n"
            "```toml\n"
            'admin_password = "원하는 비밀번호"\n'
            "```\n"
            "**배포 환경** — Streamlit Cloud → App settings → Secrets 에 같은 값을 넣으세요.\n\n"
            "비밀번호 없이 잠시 확인만 하려면 `TAXMAILER_DEV=1` 환경변수로 실행하세요."
        )
        return False

    if st.session_state.get("_admin_ok"):
        return True

    st.subheader("🔒 관리자 로그인")
    st.caption("명단·발송·이력은 관리자만 볼 수 있습니다.")
    entered = st.text_input("관리자 비밀번호", type="password", key="_admin_pw_input")
    if st.button("로그인"):
        if hmac.compare_digest(entered, password):
            st.session_state["_admin_ok"] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    return False


def logout_button() -> None:
    if st.session_state.get("_admin_ok"):
        if st.sidebar.button("로그아웃"):
            st.session_state["_admin_ok"] = False
            st.rerun()
