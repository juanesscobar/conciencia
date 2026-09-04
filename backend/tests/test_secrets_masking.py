"""Tests seguridad: `conciencia config get` NUNCA imprime secrets completos.

Fix: los valores de claves secretas (API_KEY/SECRET/PASSWORD/PASS/TOKEN) salen
enmascarados (primeros 4 chars + '… (N chars)') en tabla, single-key y --json.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from typer.testing import CliRunner

from cli import app, _mask_secret

runner = CliRunner()
TEST_DB_URL = "sqlite:///./test.db"


@pytest.fixture(autouse=True)
def _cli_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    yield


def _seed(db, key, value):
    from app.models.setting import Setting
    db.add(Setting(key=key, value=value))
    db.commit()


def test_mask_secret_helper():
    assert _mask_secret("DEEPSEEK_API_KEY", "sk-1234567890") == "sk-1… (13 chars)"
    assert _mask_secret("SMTP_PASS", "supersecreto") == "supe… (12 chars)"
    assert _mask_secret("GITHUB_TOKEN", "ghp_abc") == "ghp_… (7 chars)"
    # no secretas intactas
    assert _mask_secret("LLM_MODEL", "deepseek-chat") == "deepseek-chat"
    assert _mask_secret("SMTP_HOST", "smtp.gmail.com") == "smtp.gmail.com"
    # vacío
    assert _mask_secret("DEEPSEEK_API_KEY", "") == ""


def test_config_get_enmascara_secrets_en_tabla(db):
    _seed(db, "DEEPSEEK_API_KEY", "sk-super-secret-value-12345")
    _seed(db, "LLM_MODEL", "deepseek-chat")
    _seed(db, "SMTP_PASS", "password-gmail")

    result = runner.invoke(app, ["config", "get"])
    assert result.exit_code == 0, result.output
    assert "sk-super-secret-value-12345" not in result.output
    assert "sk-s…" in result.output or "sk-super" not in result.output
    assert "password-gmail" not in result.output
    assert "deepseek-chat" in result.output  # no-secret visible


def test_config_get_enmascara_single_key_y_json(db):
    _seed(db, "DEEPSEEK_API_KEY", "sk-super-secret-value-12345")
    _seed(db, "LLM_MODEL", "deepseek-chat")

    r1 = runner.invoke(app, ["config", "get", "DEEPSEEK_API_KEY"])
    assert "sk-super-secret-value-12345" not in r1.output
    assert "…" in r1.output

    r2 = runner.invoke(app, ["config", "get", "--json"])
    assert "sk-super-secret-value-12345" not in r2.output
    assert '"DEEPSEEK_API_KEY": "sk-s…' in r2.output or "…" in r2.output
