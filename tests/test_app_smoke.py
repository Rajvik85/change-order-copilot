"""Streamlit AppTest boot smoke checks with no API keys."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_home_boots_and_demo_loads(project_root: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = AppTest.from_file(str(project_root / "app/Home.py")).run(timeout=30)
    assert not app.exception
    assert any(
        "defensible commercial position" in markdown.value for markdown in app.markdown
    )
    load_button = next(button for button in app.button if "Load demo" in button.label)
    load_button.click()
    app.run(timeout=45)
    assert not app.exception
    assert any("18 documents analyzed" in item.value for item in app.success)


def test_dashboard_empty_state_boots(project_root: Path) -> None:
    app = AppTest.from_file(
        str(project_root / "app/pages/2_Portfolio_Dashboard.py")
    ).run(timeout=30)
    assert not app.exception
    assert any("No analysis loaded" in item.value for item in app.warning)
