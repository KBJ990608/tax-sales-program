"""테스트 공통 설정.

실제 data/ 디렉터리와 사용자 secrets 를 절대 건드리지 않도록,
모든 테스트를 임시 디렉터리에 격리한다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """store 의 저장 경로를 테스트마다 새 임시 디렉터리로 바꾼다."""
    import store

    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "SUBSCRIBERS_CSV", tmp_path / "구독자.csv")
    monkeypatch.setattr(store, "HISTORY_CSV", tmp_path / "발송이력.csv")
    yield tmp_path


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """실제 환경변수(API 키·관리자 비밀번호)가 테스트에 새어 들어오지 않게 한다."""
    for name in ("ADMIN_PASSWORD", "TAXMAILER_DEV", "ANTHROPIC_API_KEY", "TAXMAILER_DATA_DIR"):
        monkeypatch.delenv(name, raising=False)
