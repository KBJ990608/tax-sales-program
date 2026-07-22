# 세무사 콜드메일 영업 프로그램

세무 정보를 받겠다고 **직접 신청한** 사장님들에게, 업체명·대표자가 들어간 맞춤 영업 메일을 보내는 프로그램입니다. **수신 동의한 분에게만** 보내서 합법적으로 운영합니다.

## 6단계 흐름
1. **신청받기** — 사장님이 업체명·이메일 입력 + 수신 동의 체크 → `data/구독자.csv` 자동 저장
2. **명단 관리** — 잘못된 이메일·중복·발송완료를 자동 구분
3. **템플릿 선택** — 메일 5종(환영/개업축하/기장대행/법인결산/연말정산), `{업체명}{대표자}` 자동 치환
4. **발송** — "바로 발송" 버튼 → Gmail로 실제 전송
5. **이력 기록** — `data/발송이력.csv`에 저장, 같은 사람에게 같은 메일 두 번 안 감
6. **법적 준수** — 제목 `(광고)` 표기, 수신거부 안내 자동 첨부

## 로컬 실행 (개발 사이트)
```bash
cd tax-sales-program
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```
브라우저에서 `http://localhost:8501` 이 자동으로 열립니다.

## 보안 (중요)
- **관리자 잠금**: ①신청받기 화면만 공개(사장님 신청용)이고, ②명단·③발송·④이력은 **관리자 비밀번호**가 있어야 열립니다.
  - 로컬: `.streamlit/secrets.toml` 에 `admin_password = "..."` (이 파일은 git에 안 올라감). 예시는 `.streamlit/secrets.toml.example`.
  - 배포: Streamlit Cloud → App settings → **Secrets** 에 `admin_password` 설정.
- **Gmail 앱 비밀번호는 저장하지 않음**: 발송할 때 화면에 입력하며 코드/저장소에 남지 않습니다.
- **메일 헤더 인젝션 방지**: 업체명·대표자·이메일의 줄바꿈/제어문자를 제거하고 길이를 제한합니다.

## Gmail 앱 비밀번호
실제 발송에는 Gmail **앱 비밀번호**가 필요합니다(일반 비밀번호 아님).
구글 계정 → 보안 → 2단계 인증 → 앱 비밀번호 에서 16자리를 발급해 ③ 메일 보내기 화면에 입력하세요.

## Streamlit Cloud 배포 (24시간 접속)
1. 이 폴더를 GitHub 저장소로 push
2. https://share.streamlit.io 에서 저장소 연결 → `app.py` 지정 → Deploy
3. 참고: Streamlit Cloud는 파일시스템이 휘발성이라 CSV가 초기화될 수 있습니다. 실서비스로 굳히려면 Google Sheets/DB 연동이 필요합니다.

## 파일 구조
```
app.py         Streamlit UI (4개 화면)
templates.py   메일 5종 템플릿
mailer.py      Gmail SMTP 발송 + (광고)/수신거부 자동 부착
store.py       CSV 저장/검증/중복·발송여부 판정/입력 sanitize
auth.py        관리자 비밀번호 잠금
data/          구독자.csv, 발송이력.csv (자동 생성, git 제외)
.streamlit/    secrets.toml (비밀번호, git 제외)
```

> 기존 정적 HTML 파일(index.html, email_campaign.html 등)은 참고용이며, 실제 프로그램은 `app.py`입니다.
