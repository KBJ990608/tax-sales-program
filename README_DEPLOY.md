배포 안내
===========

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
 - 이미 로컬에서 테스트용 서버를 실행했습니다: `python3 -m http.server 8001 --directory /Users/1521960/Desktop/tax-sales-program`

원하면 제가 다음 작업도 해드리겠습니다:
 - Netlify에 직접 배포(사용자 토큰 필요 — 보안상 사용자 직접 연결 권장)
 - Formspree 연동용 `action` 추가 및 사용법 안내
 - GitHub 레포지토리 초기화(`git init`, `.gitignore` 설정, 커밋 명령 목록)
