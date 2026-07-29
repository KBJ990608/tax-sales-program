"""TaxMailer — 세무사 콜드메일 영업 프로그램 (Streamlit)

세무 정보를 직접 신청한(수신 동의한) 사장님들에게, 업체명·대표자가 들어간
맞춤 영업 메일을 합법적으로 보내는 프로그램.

실행: streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st

import ai
import auth
import demo
import mailer
import store
import templates

st.set_page_config(page_title="TaxMailer · 세무 영업 메일", page_icon="📧", layout="wide")

st.markdown(
    """
    <style>
      /* ── 레이아웃 기본 ───────────────────────────────────────────── */
      .stApp {overflow-x: hidden;}
      .block-container {max-width: 1200px; padding-top: 1.6rem;}
      #MainMenu, footer {visibility: hidden;}
      .stButton>button {border-radius: 12px; font-weight: 700; min-height: 48px;}
      /* 한국어는 단어 중간에서 끊지 않고 어절 단위로 줄바꿈한다. */
      .hero, .howto {word-break: keep-all;}
      /* 제목은 절대 어절 중간에서 끊지 않는다. ("챙겨드/립니다" 방지)
         Streamlit 의 heading 기본 스타일이 더 구체적이라 !important 가 필요하다. */
      .hero h1, .step b {
             word-break: keep-all !important;
             overflow-wrap: normal !important;
             text-wrap: balance;}
      /* 본문은 아주 긴 문자열(이메일 등)만 예외적으로 끊는다. */
      .hero .lead, .hero .sub, .step span {overflow-wrap: break-word;}

      /* ── 히어로 ──────────────────────────────────────────────────── */
      .hero {background: linear-gradient(135deg,#4338ca 0%,#6d28d9 100%);
             color:#fff; border-radius:24px; padding:56px 40px; margin-bottom:24px;
             box-shadow:0 24px 60px rgba(67,56,202,.28);}
      .hero .badge {display:inline-block; background:rgba(255,255,255,.18);
             padding:6px 14px; border-radius:999px; font-weight:700; font-size:.85rem;
             letter-spacing:-.01em;}
      /* 36px(모바일) ~ 64px(데스크톱) 사이에서 화면 폭에 따라 매끄럽게 변한다. */
      .hero h1 {margin:18px 0 14px; color:#fff; font-weight:800;
             font-size: clamp(2.25rem, 5.6vw, 4rem);
             line-height:1.15; letter-spacing:-0.04em;
             max-width: 16ch;}
      .hero .lead {margin:0; color:#ece9fd; max-width:720px;
             font-size: clamp(1.075rem, 1.6vw, 1.2rem); line-height:1.65;}
      .hero .sub {margin:10px 0 0; color:#c9c2f4; font-size:.94rem; line-height:1.5;}

      /* ── CTA ─────────────────────────────────────────────────────── */
      .cta-row {display:flex; flex-wrap:wrap; gap:12px; margin-top:28px;}
      /* Streamlit 기본 링크 스타일(파란색·밑줄)이 더 구체적이라 !important 로 덮는다. */
      .hero a.cta {display:inline-flex; align-items:center; justify-content:center;
             min-height:48px; padding:0 26px; border-radius:12px;
             font-weight:800; font-size:1rem;
             text-decoration:none !important;
             transition: transform .12s ease, box-shadow .12s ease, background .12s ease;}
      .hero a.cta-primary {background:#ffffff; color:#3730a3 !important;
             box-shadow:0 6px 20px rgba(0,0,0,.18);}
      .hero a.cta-primary:hover {background:#eee9ff; transform:translateY(-1px);
             box-shadow:0 10px 26px rgba(0,0,0,.24);}
      .hero a.cta-secondary {background:rgba(255,255,255,.12); color:#ffffff !important;
             border:2px solid rgba(255,255,255,.85);}
      .hero a.cta-secondary:hover {background:rgba(255,255,255,.24); transform:translateY(-1px);}
      .hero a.cta:focus-visible {outline:3px solid #fde047; outline-offset:3px;}

      /* ── 이용 방법: desktop 3열 / tablet 2열 / mobile 1열 ────────── */
      .howto {display:grid; gap:20px; margin-top:8px;
             grid-template-columns: repeat(3, minmax(0, 1fr));}
      .step {display:flex; flex-direction:column; align-items:flex-start;
             text-align:left; background:#f8fafc; border:1px solid #e6e9f2;
             border-radius:16px; padding:26px 24px; min-height:212px; height:100%;}
      /* 번호 대신 이모지를 담는 48px 라운드 박스 */
      .step .n {display:flex; align-items:center; justify-content:center;
             width:48px; height:48px; border-radius:14px; margin-bottom:16px;
             background:#ede9fe; font-size:24px; line-height:1;}
      .step b {display:block; margin:0 0 10px; color:#0f172a; font-weight:800;
             font-size: clamp(1.25rem, 1.5vw, 1.5rem); line-height:1.3;
             letter-spacing:-.02em;}
      .step span {color:#52607a; font-size: clamp(1rem, 1.15vw, 1.125rem);
             line-height:1.6;}

      /* 앵커로 스크롤할 때 상단에 여유를 둔다. */
      #apply-form, #how-it-works {scroll-margin-top: 24px;}

      /* ── 태블릿 ──────────────────────────────────────────────────── */
      @media (max-width: 1024px) {
        .howto {grid-template-columns: repeat(2, minmax(0, 1fr));}
      }

      /* ── 모바일 ──────────────────────────────────────────────────── */
      @media (max-width: 640px) {
        .block-container {padding-left:20px; padding-right:20px;}
        .hero {padding:32px 24px 40px; border-radius:20px;}
        .hero h1 {max-width: 100%; font-size: clamp(2.25rem, 9.5vw, 2.625rem);}
        .hero .lead {font-size:1.125rem; line-height:1.65;}
        .cta-row {flex-direction:column; gap:10px;}
        .cta {width:100%;}
        .howto {grid-template-columns: 1fr; gap:16px;}
        .step {min-height:0; padding:24px;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)

PAGES = ["① 신청받기", "② 명단 관리", "③ 메일 보내기", "④ 발송 이력"]


def secret(name: str, default: str = "") -> str:
    """secrets.toml → 환경변수 순으로 설정값을 읽는다. 없으면 빈 문자열."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # secrets.toml 자체가 없는 로컬 환경
        pass
    return os.environ.get(name.upper(), default)


# ── 데이터 접근 라우팅 ────────────────────────────────────────────────────
# 화면은 아래 함수들만 쓴다. 데모 모드일 때는 세션 메모리를, 아니면 실제 CSV를
# 본다. 분기를 여기 한 곳에 모아 두어야 "데모인데 실제 파일을 건드리는" 실수가
# 생기지 않는다.
def current_subscribers() -> list[dict]:
    return demo.demo_subscribers() if demo.is_demo_mode() else store.load_subscribers()


def current_history() -> list[dict]:
    return demo.demo_history() if demo.is_demo_mode() else store.load_history()


def current_candidates(template_name: str) -> list[dict]:
    """이 템플릿을 아직 안 받은 유효 대상. 실제/데모 모두 같은 판정 로직."""
    history = current_history()
    return [
        r for r in store.clean_rows(current_subscribers())
        if not store.has_sent(history, r.get("이메일", ""), template_name)
    ]


def remove_subscriber(email: str) -> None:
    if demo.is_demo_mode():
        demo.demo_delete_subscriber(email)
    else:
        store.delete_subscriber(email)


with st.sidebar:
    st.title("📧 TaxMailer")
    st.caption("동의한 사장님에게만 맞춤 메일을 보냅니다.")
    page = st.radio("메뉴", PAGES, label_visibility="collapsed", key="nav_menu")
    st.divider()
    st.caption(f"현재 모드: **{'데모' if demo.is_demo_mode() else '실제 데이터'}**")
    auth.logout_button()

# 신청받기는 공개(사장님 신청용), 나머지 관리 화면은 관리자 인증 필요
if page != "① 신청받기" and not auth.require_admin():
    st.stop()

# 관리 화면 상단에는 어느 데이터를 보고 있는지 항상 띄워 둔다.
if page != "① 신청받기" and demo.is_demo_mode():
    st.info(demo.BANNER)


# ─────────────────────────────── ① 신청받기 (공개 랜딩) ───────────────────────────────
if page == "① 신청받기":
    # 히어로 + CTA. 카드는 st.columns 대신 CSS grid 로 그려서 화면 폭에 따라
    # 3열 → 2열 → 1열로 접히게 한다. (st.columns 는 모바일에서도 가로를 유지한다)
    st.markdown(
        """
        <section class="hero">
          <span class="badge">사업자 전용 · 무료 세무 안내</span>
          <h1>놓치기 쉬운 세금 일정, 미리 챙겨드립니다</h1>
          <p class="lead">업체명과 이메일을 남겨주시면 업종별 신고 일정과
          세무 체크포인트를 보내드립니다.</p>
          <p class="sub">언제든 수신거부할 수 있습니다.</p>
          <div class="cta-row">
            <a class="cta cta-primary" href="#apply-form">무료 세무 안내 신청하기</a>
            <a class="cta cta-secondary" href="#how-it-works">서비스 이용 방법</a>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    # 앵커는 Streamlit 의 anchor= 로 만든다. raw HTML 의 id 는 렌더링 시
    # 임의 해시로 교체되어 #링크가 동작하지 않는다.
    st.subheader("서비스 이용 방법", anchor="how-it-works")
    st.markdown(
        """
        <div class="howto">
          <div class="step">
            <span class="n" aria-hidden="true">🧾</span>
            <b>신청서 작성</b>
            <span>업체명과 이메일을 남기고 수신에 동의합니다.</span>
          </div>
          <div class="step">
            <span class="n" aria-hidden="true">⏰</span>
            <b>맞춤 안내 수신</b>
            <span>업종에 맞는 신고 일정과 체크포인트를 메일로 받습니다.</span>
          </div>
          <div class="step">
            <span class="n" aria-hidden="true">💬</span>
            <b>필요할 때 상담</b>
            <span>궁금한 점이 생기면 메일로 회신해 상담을 이어갑니다.</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.subheader("무료 세무 안내 신청", anchor="apply-form")
        with st.form("apply", clear_on_submit=True):
            company = st.text_input("업체명 *", placeholder="예: 행복상사")
            ceo = st.text_input("대표자 이름", placeholder="예: 홍길동")
            email = st.text_input("이메일 *", placeholder="example@company.com")
            agreed = st.checkbox("세무 정보/영업 메일 수신에 동의합니다. *")
            submitted = st.form_submit_button("무료로 신청하기", width="stretch", type="primary")

        if submitted:
            ok, msg = store.add_subscriber(company, ceo, email, agreed)
            (st.success if ok else st.error)(msg)
        st.caption("입력하신 정보는 세무 안내 메일 발송에만 사용되며, 수신거부 시 즉시 중단됩니다.")


# ─────────────────────────────── ② 명단 관리 ───────────────────────────────
elif page == "② 명단 관리":
    st.header("② 명단 관리")
    st.caption("잘못된 이메일·중복·이미 보낸 사람을 자동으로 구분해서 보여줍니다.")

    # ── 데모 데이터 ───────────────────────────────────────────────────────
    st.subheader("데모 데이터")
    st.caption(demo.INTRO)

    if demo.is_demo_mode():
        if st.button("데모 종료", key="demo_stop", type="primary"):
            demo.stop_demo()
            st.rerun()
    else:
        if st.button("데모 데이터 불러오기", key="demo_start", type="primary"):
            try:
                demo.start_demo()
            except demo.DemoDataError as exc:
                st.error(str(exc))
            else:
                st.rerun()

    st.divider()

    if not demo.is_demo_mode():
        st.caption(
            "⚠️ 명단은 CSV 파일로 저장됩니다. Streamlit Community Cloud처럼 앱을 다시 배포하면 "
            "디스크가 초기화되는 환경에서는 아래 **명단 CSV 내려받기**로 주기적으로 백업하세요."
        )

    subs = current_subscribers()
    if not subs:
        st.info("아직 신청자가 없습니다. ① 신청받기에서 등록하거나, 위에서 데모 데이터를 불러와 보세요.")
    else:
        history = current_history()
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
        st.dataframe(df, width="stretch", hide_index=True)

        st.download_button(
            "명단 CSV 내려받기",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name="데모_구독자명단.csv" if demo.is_demo_mode() else "구독자명단.csv",
            mime="text/csv",
            help="배포 환경에서는 저장 파일이 재배포 시 사라질 수 있으니 주기적으로 받아두세요.",
        )

        st.subheader("항목 삭제")
        del_email = st.selectbox("삭제할 구독자 이메일", [""] + [r.get("이메일", "") for r in subs])
        if st.button("삭제", type="secondary") and del_email:
            remove_subscriber(del_email)
            st.success(f"{del_email} 삭제했습니다.")
            st.rerun()


# ─────────────────────────────── ③ 메일 보내기 ───────────────────────────────
elif page == "③ 메일 보내기":
    st.header("③ 메일 보내기")

    result = st.session_state.pop("send_result", None)
    if result:
        st.success(result["message"])
        if result["failed"]:
            st.error(
                f"실패 {len(result['failed'])}건:\n" + "\n".join(result["failed"])
            )

    st.subheader("1. 발신 Gmail 설정")
    if demo.is_demo_mode():
        # 데모에서는 SMTP를 아예 쓰지 않으므로 계정 입력을 받지 않는다.
        sender_email = sender_name = app_password = ""
        st.info("데모 모드에서는 실제 발송을 하지 않으므로 Gmail 계정이 필요하지 않습니다.")
    else:
        # secrets/환경변수에 넣어두면 세션마다 다시 입력하지 않아도 된다.
        c1, c2 = st.columns(2)
        sender_email = c1.text_input(
            "발신 Gmail 주소", value=secret("gmail_address"), placeholder="you@gmail.com"
        )
        sender_name = c2.text_input(
            "발신자 이름", value=secret("sender_name"), placeholder="예: 행복세무회계 김세무"
        )
        app_password = st.text_input(
            "Gmail 앱 비밀번호", type="password", value=secret("gmail_app_password"),
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

    candidates = current_candidates(template_name)

    st.subheader("3. 발송 대상")
    if not candidates:
        st.info("이 템플릿을 보낼 대상이 없습니다. (신청자가 없거나, 모두에게 이미 보냈습니다)")
    else:
        st.write(f"이 템플릿을 아직 안 받은 대상: **{len(candidates)}명**")
        preview_rows = [
            {"업체명": r.get("업체명", ""), "대표자": r.get("대표자", ""), "이메일": r.get("이메일", "")}
            for r in candidates
        ]
        st.dataframe(pd.DataFrame(preview_rows), width="stretch", hide_index=True)

        sample = candidates[0]
        subj, body = render_for(sample.get("업체명", ""), sample.get("대표자", ""))
        with st.expander("📄 미리보기 (첫 번째 대상 기준 — 실제 발송 형태)", expanded=True):
            st.text(f"제목: {mailer.with_ad_prefix(subj)}")
            st.text(mailer.with_unsubscribe(body))

        st.subheader("4. 발송")
        st.caption("제목에 (광고), 본문에 수신거부 안내가 자동으로 붙습니다.")

        if demo.is_demo_mode():
            # ── 데모 발송 ─────────────────────────────────────────────────
            # 이 분기에서는 mailer.send_gmail 을 호출하지 않는다. 발송을
            # 흉내만 내고 세션 이력에만 기록하므로 실제 메일은 나가지 않는다.
            st.caption("데모 모드입니다. 실제 이메일은 전송되지 않습니다.")
            confirmed = st.checkbox(
                f"미리보기를 확인했으며, 데모 대상 {len(candidates)}명에 대해 발송을 시뮬레이션합니다."
            )
            if st.button("🧪 데모 발송 실행", type="primary", disabled=not confirmed):
                if mode == "🤖 AI 맞춤 생성" and not (body_tmpl or "").strip():
                    st.error("먼저 AI로 문안을 생성하거나 본문 템플릿을 입력해 주세요.")
                else:
                    progress = st.progress(0.0)
                    sent = 0
                    for i, r in enumerate(candidates):
                        company = r.get("업체명", "")
                        ceo = r.get("대표자", "")
                        to_email = r.get("이메일", "")
                        subj, _body = render_for(company, ceo)
                        demo.record_demo_send(
                            to_email, company, ceo, template_name,
                            mailer.with_ad_prefix(subj), store.now(),
                        )
                        sent += 1
                        progress.progress((i + 1) / len(candidates))

                    st.session_state["send_result"] = {
                        "message": f"{demo.SEND_DONE} (데모 이력 {sent}건 추가)",
                        "failed": [],
                    }
                    st.rerun()
        else:
            # ── 실제 발송 ─────────────────────────────────────────────────
            # 실제 외부 발송은 되돌릴 수 없으므로 미리보기를 확인했다는 체크를 요구한다.
            confirmed = st.checkbox(
                f"위 미리보기를 확인했으며, {len(candidates)}명에게 실제로 발송합니다."
            )
            if st.button("🚀 바로 발송", type="primary", disabled=not confirmed):
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
                                sender_email, app_password, to_email, subj, body,
                                sender_name or None,
                            )
                            store.record_send(to_email, company, ceo, template_name, full_subject)
                            sent += 1
                        except Exception as e:  # noqa: BLE001
                            failed.append(f"{to_email}: {e}")
                        progress.progress((i + 1) / len(candidates))

                    # rerun 하면 이 자리의 메시지가 지워지므로 결과를 남겨 두고
                    # 다시 그린 화면 위쪽에서 표시한다.
                    st.session_state["send_result"] = {
                        "message": f"발송 완료: {sent}건",
                        "failed": failed,
                    }
                    st.rerun()


# ─────────────────────────────── ④ 발송 이력 ───────────────────────────────
elif page == "④ 발송 이력":
    st.header("④ 발송 이력")
    st.caption("누구에게 언제 어떤 메일을 보냈는지 기록입니다. 같은 사람에게 같은 템플릿은 다시 안 갑니다.")

    history = current_history()
    if not history:
        st.info("아직 발송 이력이 없습니다. ② 명단 관리에서 데모 데이터를 불러오면 예시 이력을 볼 수 있습니다.")
    else:
        df = pd.DataFrame(history)
        st.metric("누적 발송", f"{len(df)}건")
        st.dataframe(df, width="stretch", hide_index=True)
        st.download_button(
            "이력 CSV 다운로드",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name="데모_발송이력.csv" if demo.is_demo_mode() else "발송이력.csv",
            mime="text/csv",
        )
