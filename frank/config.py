"""
Frank configuration and state management.

Provides first-run detection, persistent configuration storage,
and API key management under ~/.frank/.
"""

import json
import os
from typing import Optional


def _get_config_dir() -> str:
    """Return the Frank configuration directory path."""
    path = os.path.expanduser("~/.frank")
    os.makedirs(path, exist_ok=True)
    return path


def _load_config_json() -> dict:
    """Load the JSON config file, returning {} if absent or corrupt."""
    config_path = os.path.join(_get_config_dir(), "config.json")
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def is_first_run() -> bool:
    """Check whether this is the first time Frank has been launched."""
    marker = os.path.join(_get_config_dir(), "onboarded")
    return not os.path.exists(marker)


def mark_onboarded() -> None:
    """Record that the onboarding guide has been displayed."""
    marker = os.path.join(_get_config_dir(), "onboarded")
    with open(marker, "w") as f:
        f.write("1\n")


def get_config_dir() -> str:
    """Return the Frank configuration directory, creating it if needed."""
    return _get_config_dir()


def get_api_key() -> Optional[str]:
    """Return the DeepSeek API key from config, or None if not set."""
    config = _load_config_json()
    return config.get("deepseek_api_key")


def set_api_key(key: str) -> None:
    """Store the DeepSeek API key in the config file with restricted permissions."""
    config_path = os.path.join(_get_config_dir(), "config.json")
    config = _load_config_json()
    config["deepseek_api_key"] = key
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(config_path, 0o600)


def get_model_name() -> str:
    """Return the configured LLM model name."""
    config = _load_config_json()
    return config.get("deepseek_model", "deepseek-chat")


def get_runs_dir() -> str:
    """Return the directory for persistent calculation runs."""
    config = _load_config_json()
    default = os.path.join(_get_config_dir(), "runs")
    path = config.get("runs_dir", default)
    os.makedirs(path, exist_ok=True)
    return path


def get_save_runs() -> bool:
    """Whether to persist calculation runs to disk (Aitomia-style)."""
    config = _load_config_json()
    return config.get("save_runs", True)


def set_save_runs(enabled: bool) -> None:
    """Enable or disable persistent run directories."""
    config_path = os.path.join(_get_config_dir(), "config.json")
    config = _load_config_json()
    config["save_runs"] = enabled
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def get_database_url() -> str:
    """Return SQLAlchemy database URL (PostgreSQL or SQLite fallback)."""
    env = os.environ.get("FRANK_DATABASE_URL")
    if env:
        return env
    config = _load_config_json()
    if config.get("database_url"):
        return config["database_url"]
    default_sqlite = os.path.join(_get_config_dir(), "frank.db")
    return f"sqlite:///{default_sqlite}"


def get_redis_url() -> str:
    """Return Redis URL for pub/sub progress."""
    env = os.environ.get("FRANK_REDIS_URL")
    if env:
        return env
    config = _load_config_json()
    return config.get("redis_url", "redis://localhost:6379/0")


def get_broker_url() -> str:
    """Return Celery broker URL."""
    env = os.environ.get("FRANK_BROKER_URL")
    if env:
        return env
    config = _load_config_json()
    return config.get("broker_url", get_redis_url())


def get_result_backend_url() -> str:
    """Return Celery result backend URL."""
    env = os.environ.get("FRANK_RESULT_BACKEND")
    if env:
        return env
    config = _load_config_json()
    return config.get("result_backend", get_redis_url())


def get_store_enabled() -> bool:
    """Whether to persist calculation jobs to CalcStore."""
    env = os.environ.get("FRANK_STORE_ENABLED")
    if env is not None:
        return env.lower() in ("1", "true", "yes", "on")
    config = _load_config_json()
    return config.get("store_enabled", True)


def set_store_enabled(enabled: bool) -> None:
    """Enable or disable CalcStore persistence."""
    config_path = os.path.join(_get_config_dir(), "config.json")
    config = _load_config_json()
    config["store_enabled"] = enabled
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
