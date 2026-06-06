from pathlib import Path


def test_env_example_uses_unified_xf_credentials() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "XF_APPID=" in env_example
    assert "XF_APIKEY=" in env_example
    assert "XF_SECRET=" in env_example
    assert "XF_SPARK_API_URL=" in env_example
    assert "XF_SPARK_DOMAIN=" in env_example
    assert "0bd5e475" not in env_example


def test_gitignore_blocks_private_env_and_python_cache() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert "__pycache__/" in gitignore
    assert "*.pyc" in gitignore
