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


def require_admin() -> bool:
    """관리자 인증 통과 시 True. 아니면 로그인 폼을 그리고 False.

    비밀번호가 아예 설정돼 있지 않으면(로컬 개발) 경고만 띄우고 통과시킨다.
    """
    password = _configured_password()

    if not password:
        st.warning(
            "⚠️ 관리자 비밀번호가 설정되지 않았습니다(로컬 개발 모드). "
            "배포 전 반드시 secrets에 `admin_password`를 설정하세요."
        )
        return True

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
