배포 안내 (레거시 정적 사이트 전용)
===================================

> ⚠️ 이 문서는 저장소에 함께 들어 있는 **옛 정적 HTML 페이지**(`index.html`, `landing.html`,
> `tax_sales_simple.html` 등)를 공개하는 방법입니다.
> 현재 프로그램인 **Streamlit 앱(`app.py`)의 배포 방법은 [README.md](README.md) 의
> "배포 (Streamlit Community Cloud)" 절**을 보세요.

간단히 정적 사이트를 서비스 형태로 공개하는 방법 두 가지를 안내합니다.

1) Netlify (권장 — 폼 수집 포함)
 - 계정 생성 후 새 사이트 만들기 → "Deploy manually"(Drag & Drop)로 `tax-sales-program` 폴더를 업로드하세요.
 - 또는 Git 연동으로 배포합니다. 루트에 `netlify.toml`이 있으므로 루트가 퍼블리시됩니다.
 - Netlify Forms를 사용하려면 `tax_sales_simple.html`의 `<form name="lead-form" data-netlify="true">`이 이미 설정되어 있습니다.
 - 빌드 후 Netlify 대시보드의 "Forms"에서 제출 내역을 확인할 수 있습니다.

2) GitHub Pages
 - 레포지토리를 생성하고 파일을 푸시하세요.
 - repository settings → Pages에서 `main` 브랜치의 `/(root)`를 배포 대상으로 선택하면 공개됩니다.
 - GitHub Pages는 서버 사이드 폼 처리를 제공하지 않습니다. 폼 제출을 원하면 Formspree 혹은 Google Forms로 전환하세요.

로컬 테스트
 - 저장소 루트에서 `python3 -m http.server 8001` 을 실행하고 `http://localhost:8001` 을 엽니다.
