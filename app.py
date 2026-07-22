"""TaxMailer — 세무사 콜드메일 영업 프로그램 (Streamlit)

세무 정보를 직접 신청한(수신 동의한) 사장님들에게, 업체명·대표자가 들어간
맞춤 영업 메일을 합법적으로 보내는 프로그램.

실행: streamlit run app.py
"""
import pandas as pd
import streamlit as st

import ai
import auth
import mailer
import store
import templates

st.set_page_config(page_title="TaxMailer · 세무 영업 메일", page_icon="📧", layout="wide")

st.markdown(
    """
    <style>
      .block-container {max-width: 1080px; padding-top: 1.6rem;}
      #MainMenu, footer {visibility: hidden;}
      .stButton>button {border-radius: 12px; font-weight: 700;}
      /* 랜딩 히어로 */
      .hero {background: linear-gradient(135deg,#4338ca 0%,#6d28d9 100%);
             color:#fff; border-radius:24px; padding:36px 40px; margin-bottom:24px;
             box-shadow:0 24px 60px rgba(67,56,202,.28);}
      .hero .badge {display:inline-block; background:rgba(255,255,255,.18);
             padding:6px 14px; border-radius:999px; font-weight:700; font-size:.85rem;}
      .hero h1 {margin:14px 0 8px; font-size:2rem; line-height:1.25; color:#fff;}
      .hero p {margin:0; color:#e9e7fb; font-size:1.02rem; line-height:1.6;}
      .benefit {background:#f8fafc; border:1px solid #e6e9f2; border-radius:16px;
             padding:18px 18px; height:100%;}
      .benefit b {display:block; margin-bottom:6px; font-size:1rem;}
      .benefit span {color:#52607a; font-size:.92rem; line-height:1.55;}
    </style>
    """,
    unsafe_allow_html=True,
)

PAGES = ["① 신청받기", "② 명단 관리", "③ 메일 보내기", "④ 발송 이력"]

with st.sidebar:
    st.title("📧 TaxMailer")
    st.caption("동의한 사장님에게만 맞춤 메일을 보냅니다.")
    page = st.radio("메뉴", PAGES, label_visibility="collapsed")
    st.divider()
    subs = store.load_subscribers()
    hist = store.load_history()
    st.metric("구독자", f"{len(subs)}명")
    st.metric("누적 발송", f"{len(hist)}건")
    auth.logout_button()

# 신청받기는 공개(사장님 신청용), 나머지 관리 화면은 관리자 인증 필요
if page != "① 신청받기" and not auth.require_admin():
    st.stop()


# ─────────────────────────────── ① 신청받기 (공개 랜딩) ───────────────────────────────
if page == "① 신청받기":
    st.markdown(
        """
        <div class="hero">
          <span class="badge">사업자 전용 · 무료 세무 안내</span>
          <h1>부가세·종합소득세, 놓치기 쉬운 것부터 챙겨드립니다</h1>
          <p>업체명과 이메일만 남겨주시면, 사장님 업종에 맞는 세무 체크포인트와 절세 안내를
          메일로 보내드립니다. 원치 않으시면 언제든 수신거부하실 수 있습니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2, b3 = st.columns(3)
    b1.markdown('<div class="benefit"><b>🧾 업종별 체크리스트</b><span>온라인셀러·1인사업자·법인에 맞춘 신고 포인트</span></div>', unsafe_allow_html=True)
    b2.markdown('<div class="benefit"><b>⏰ 신고 일정 알림</b><span>부가세·종소세·법인결산 시즌 미리 안내</span></div>', unsafe_allow_html=True)
    b3.markdown('<div class="benefit"><b>💬 부담 없는 상담</b><span>필요할 때만, 원하실 때 회신으로 연결</span></div>', unsafe_allow_html=True)

    st.write("")
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.subheader("무료 세무 안내 신청")
        with st.form("apply", clear_on_submit=True):
            company = st.text_input("업체명 *", placeholder="예: 행복상사")
            ceo = st.text_input("대표자 이름", placeholder="예: 홍길동")
            email = st.text_input("이메일 *", placeholder="example@company.com")
            agreed = st.checkbox("세무 정보/영업 메일 수신에 동의합니다. *")
            submitted = st.form_submit_button("무료로 신청하기", use_container_width=True, type="primary")

        if submitted:
            ok, msg = store.add_subscriber(company, ceo, email, agreed)
            (st.success if ok else st.error)(msg)
        st.caption("입력하신 정보는 세무 안내 메일 발송에만 사용되며, 수신거부 시 즉시 중단됩니다.")


# ─────────────────────────────── ② 명단 관리 ───────────────────────────────
elif page == "② 명단 관리":
    st.header("② 명단 관리")
    st.caption("잘못된 이메일·중복·이미 보낸 사람을 자동으로 구분해서 보여줍니다.")

    subs = store.load_subscribers()
    if not subs:
        st.info("아직 신청자가 없습니다. ① 신청받기에서 등록해 보세요.")
    else:
        history = store.load_history()
        sent_emails = {h.get("이메일", "").strip().lower() for h in history}
        seen: set[str] = set()
        rows = []
        for r in subs:
            email = r.get("이메일", "").strip()
            key = email.lower()
            if not store.is_valid_email(email):
                status = "❌ 잘못된 이메일"
            elif key in seen:
                status = "⚠️ 중복"
            elif key in sent_emails:
                status = "✅ 발송완료"
            else:
                status = "🟢 발송대기"
            seen.add(key)
            rows.append({
                "상태": status,
                "업체명": r.get("업체명", ""),
                "대표자": r.get("대표자", ""),
                "이메일": email,
                "신청일시": r.get("신청일시", ""),
            })
        df = pd.DataFrame(rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("발송대기", int((df["상태"] == "🟢 발송대기").sum()))
        c2.metric("발송완료", int((df["상태"] == "✅ 발송완료").sum()))
        c3.metric("확인필요", int(df["상태"].isin(["❌ 잘못된 이메일", "⚠️ 중복"]).sum()))
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("항목 삭제")
        del_email = st.selectbox("삭제할 구독자 이메일", [""] + [r.get("이메일", "") for r in subs])
        if st.button("삭제", type="secondary") and del_email:
            store.delete_subscriber(del_email)
            st.success(f"{del_email} 삭제했습니다.")
            st.rerun()


# ─────────────────────────────── ③ 메일 보내기 ───────────────────────────────
elif page == "③ 메일 보내기":
    st.header("③ 메일 보내기")

    st.subheader("1. 발신 Gmail 설정")
    c1, c2 = st.columns(2)
    sender_email = c1.text_input("발신 Gmail 주소", placeholder="you@gmail.com")
    sender_name = c2.text_input("발신자 이름", placeholder="예: 행복세무회계 김세무")
    app_password = st.text_input(
        "Gmail 앱 비밀번호", type="password",
        help="구글 계정 → 보안 → 2단계 인증 → 앱 비밀번호에서 발급한 16자리. 일반 비밀번호가 아닙니다.",
    )

    st.subheader("2. 템플릿 선택")
    mode = st.radio("문안 방식", ["고정 템플릿 5종", "🤖 AI 맞춤 생성"], horizontal=True)

    if mode == "고정 템플릿 5종":
        template_name = st.selectbox("메일 종류", templates.template_names())
        subj_tmpl = body_tmpl = None
    else:
        template_name = "AI맞춤"
        if not ai.has_key():
            st.warning(
                "AI 생성에는 Anthropic API 키가 필요합니다. "
                "`.streamlit/secrets.toml` 의 `anthropic_api_key` 또는 환경변수 `ANTHROPIC_API_KEY`를 설정하세요."
            )
        c1, c2 = st.columns([2, 1])
        brief = c1.text_input("메일 목적/내용", placeholder="예: 기장대행 상담 제안, 봄 신규 사업자 대상")
        tone = c2.text_input("톤", placeholder="예: 담백하고 정중하게")
        if st.button("✨ AI로 문안 생성", disabled=not ai.has_key()):
            with st.spinner("Claude가 문안을 작성 중입니다..."):
                try:
                    s, b = ai.generate_template(brief, tone)
                    st.session_state["ai_subject"] = s
                    st.session_state["ai_body"] = b
                    st.success("생성 완료! 아래에서 수정할 수 있어요.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"생성 실패: {e}")
        subj_tmpl = st.text_input("제목 템플릿", value=st.session_state.get("ai_subject", ""))
        body_tmpl = st.text_area("본문 템플릿", value=st.session_state.get("ai_body", ""), height=220)
        st.caption("`{업체명}` `{대표자}` 는 발송 시 각 구독자 값으로 자동 치환됩니다.")

    def render_for(company, ceo):
        if mode == "고정 템플릿 5종":
            return templates.render(template_name, company, ceo)
        return templates.render_raw(subj_tmpl or "", body_tmpl or "", company, ceo)

    candidates = [
        r for r in store.clean_subscribers()
        if not store.already_sent(r.get("이메일", ""), template_name)
    ]

    st.subheader("3. 발송 대상")
    if not candidates:
        st.info("이 템플릿을 보낼 대상이 없습니다. (신청자가 없거나, 모두에게 이미 보냈습니다)")
    else:
        st.write(f"이 템플릿을 아직 안 받은 대상: **{len(candidates)}명**")
        preview_rows = [
            {"업체명": r.get("업체명", ""), "대표자": r.get("대표자", ""), "이메일": r.get("이메일", "")}
            for r in candidates
        ]
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

        sample = candidates[0]
        subj, body = render_for(sample.get("업체명", ""), sample.get("대표자", ""))
        with st.expander("📄 미리보기 (첫 번째 대상 기준 — 실제 발송 형태)", expanded=True):
            st.text(f"제목: {mailer.with_ad_prefix(subj)}")
            st.text(mailer.with_unsubscribe(body))

        st.subheader("4. 발송")
        st.caption("제목에 (광고), 본문에 수신거부 안내가 자동으로 붙습니다.")
        if st.button("🚀 바로 발송", type="primary"):
            if not sender_email or not app_password:
                st.error("발신 Gmail 주소와 앱 비밀번호를 입력해 주세요.")
            elif mode == "🤖 AI 맞춤 생성" and not (body_tmpl or "").strip():
                st.error("먼저 AI로 문안을 생성하거나 본문 템플릿을 입력해 주세요.")
            else:
                progress = st.progress(0.0)
                sent, failed = 0, []
                for i, r in enumerate(candidates):
                    company = r.get("업체명", "")
                    ceo = r.get("대표자", "")
                    to_email = r.get("이메일", "")
                    subj, body = render_for(company, ceo)
                    try:
                        full_subject = mailer.send_gmail(
                            sender_email, app_password, to_email, subj, body, sender_name or None
                        )
                        store.record_send(to_email, company, ceo, template_name, full_subject)
                        sent += 1
                    except Exception as e:  # noqa: BLE001
                        failed.append(f"{to_email}: {e}")
                    progress.progress((i + 1) / len(candidates))

                st.success(f"발송 완료: {sent}건")
                if failed:
                    st.error("실패 " + str(len(failed)) + "건:\n" + "\n".join(failed))
                st.rerun()


# ─────────────────────────────── ④ 발송 이력 ───────────────────────────────
elif page == "④ 발송 이력":
    st.header("④ 발송 이력")
    st.caption("누구에게 언제 어떤 메일을 보냈는지 기록입니다. 같은 사람에게 같은 템플릿은 다시 안 갑니다.")

    history = store.load_history()
    if not history:
        st.info("아직 발송 이력이 없습니다.")
    else:
        df = pd.DataFrame(history)
        st.metric("누적 발송", f"{len(df)}건")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "이력 CSV 다운로드",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name="발송이력.csv",
            mime="text/csv",
        )
