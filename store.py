"""구독자 명단과 발송 이력을 CSV로 저장/조회하는 헬퍼.

- data/구독자.csv : 신청한 사장님 명단
- data/발송이력.csv : 누구에게 언제 어떤 템플릿을 보냈는지 기록

파일 기반이라 별도 DB 없이 동작한다. (Streamlit Cloud 배포 시에는 휘발성)
"""
import csv
import os
import re
from datetime import datetime
from pathlib import Path

# 저장 위치는 환경변수로 바꿀 수 있다. Streamlit Cloud 처럼 앱 디렉터리가
# 재배포마다 초기화되는 환경에서 영구 볼륨을 가리키거나, 테스트에서 임시
# 디렉터리로 격리하기 위해서다.
DATA_DIR = Path(os.environ.get("TAXMAILER_DATA_DIR", str(Path(__file__).parent / "data")))
SUBSCRIBERS_CSV = DATA_DIR / "구독자.csv"
HISTORY_CSV = DATA_DIR / "발송이력.csv"

SUBSCRIBER_FIELDS = ["업체명", "대표자", "이메일", "수신동의", "신청일시"]
HISTORY_FIELDS = ["이메일", "업체명", "대표자", "템플릿", "제목", "발송일시"]

# 간단한 이메일 형식 검증용 정규식
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def now() -> str:
    """CSV에 기록하는 시각 문자열. 데모 이력도 같은 형식을 쓴다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_now = now  # 기존 내부 호출 호환


def _ensure(path: Path, fields: list[str]) -> None:
    """CSV가 없으면 헤더만 만들어 둔다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()


def sanitize(text: str, limit: int = 200) -> str:
    """줄바꿈·제어문자를 제거해 메일 헤더 인젝션을 막고 길이를 제한한다."""
    text = (text or "").replace("\r", " ").replace("\n", " ")
    text = "".join(ch for ch in text if ch == "\t" or ord(ch) >= 32)
    return text.strip()[:limit]


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match((email or "").strip()))


def load_subscribers() -> list[dict]:
    _ensure(SUBSCRIBERS_CSV, SUBSCRIBER_FIELDS)
    with SUBSCRIBERS_CSV.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_history() -> list[dict]:
    _ensure(HISTORY_CSV, HISTORY_FIELDS)
    with HISTORY_CSV.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def email_exists(email: str) -> bool:
    """이미 구독자 명단에 있는 이메일인지(중복 신청 방지)."""
    target = (email or "").strip().lower()
    return any(r.get("이메일", "").strip().lower() == target for r in load_subscribers())


def add_subscriber(company: str, ceo: str, email: str, agreed: bool) -> tuple[bool, str]:
    """구독자 1명 추가. (성공여부, 메시지) 반환.

    - 수신 동의 필수: 미동의 시 저장 거부 (합법성의 핵심)
    - 이메일 형식 검증
    - 중복 이메일 거부
    """
    company = sanitize(company)
    ceo = sanitize(ceo, limit=50)
    email = sanitize(email, limit=254)

    if not company:
        return False, "업체명을 입력해 주세요."
    if not is_valid_email(email):
        return False, "이메일 형식이 올바르지 않습니다."
    if not agreed:
        return False, "수신 동의에 체크해야 신청할 수 있습니다. (동의한 분에게만 발송합니다)"
    if email_exists(email):
        return False, "이미 신청된 이메일입니다."

    _ensure(SUBSCRIBERS_CSV, SUBSCRIBER_FIELDS)
    with SUBSCRIBERS_CSV.open("a", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=SUBSCRIBER_FIELDS).writerow(
            {
                "업체명": company,
                "대표자": ceo,
                "이메일": email,
                "수신동의": "동의",
                "신청일시": _now(),
            }
        )
    return True, f"{company} 사장님, 신청이 완료되었습니다."


def delete_subscriber(email: str) -> None:
    rows = [r for r in load_subscribers() if r.get("이메일", "").strip().lower() != (email or "").strip().lower()]
    with SUBSCRIBERS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=SUBSCRIBER_FIELDS)
        w.writeheader()
        w.writerows(rows)


def has_sent(history: list[dict], email: str, template_name: str) -> bool:
    """주어진 이력 목록 안에 (이메일, 템플릿) 조합이 있는지.

    파일을 읽지 않는 순수 함수라, 데모 모드처럼 이력이 메모리에만 있는
    경우에도 같은 판정 로직을 그대로 쓸 수 있다.
    """
    target = (email or "").strip().lower()
    return any(
        r.get("이메일", "").strip().lower() == target and r.get("템플릿", "") == template_name
        for r in history
    )


def already_sent(email: str, template_name: str) -> bool:
    """같은 사람에게 같은 템플릿(캠페인)을 이미 보냈는지. (실제 데이터 기준)"""
    return has_sent(load_history(), email, template_name)


def record_send(email: str, company: str, ceo: str, template_name: str, subject: str) -> None:
    _ensure(HISTORY_CSV, HISTORY_FIELDS)
    with HISTORY_CSV.open("a", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=HISTORY_FIELDS).writerow(
            {
                "이메일": email,
                "업체명": company,
                "대표자": ceo,
                "템플릿": template_name,
                "제목": subject,
                "발송일시": _now(),
            }
        )


def clean_rows(rows: list[dict]) -> list[dict]:
    """유효한(이메일 형식 정상) 행만 반환. 중복은 최초 1건만.

    파일을 읽지 않는 순수 함수. 데모 모드도 이 함수를 그대로 써서
    실제 발송 대상 추출 로직과 동일하게 동작한다.
    """
    seen: set[str] = set()
    cleaned = []
    for r in rows:
        email = r.get("이메일", "").strip().lower()
        if not is_valid_email(email) or email in seen:
            continue
        seen.add(email)
        cleaned.append(r)
    return cleaned


def clean_subscribers() -> list[dict]:
    """유효한 구독자만 반환. (실제 데이터 기준)"""
    return clean_rows(load_subscribers())
