import tomllib
from pathlib import Path

import src.main as main


def test_console_script_points_to_src_main_serve() -> None:
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text()
    )

    assert pyproject["project"]["scripts"] == {"aic-pipeline": "src.main:serve"}


def test_serve_uses_one_uppercase_log_level(monkeypatch) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(main.app_config, "PIPELINE_LOG_LEVEL", "debug")
    monkeypatch.setattr(
        main.logging,
        "basicConfig",
        lambda **kwargs: calls.setdefault("logging", kwargs),
    )
    monkeypatch.setattr(
        main.uvicorn,
        "run",
        lambda *args, **kwargs: calls.setdefault("uvicorn", (args, kwargs)),
    )

    main.serve()

    assert calls["logging"] == {"level": "DEBUG"}
    assert calls["uvicorn"] == (
        ("src.main:app",),
        {"host": "0.0.0.0", "port": 8000, "log_level": "DEBUG"},
    )
