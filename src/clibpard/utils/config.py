"""Configuration management."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Application configuration."""

    device_id: str
    device_name: str
    data_dir: Path
    db_path: Path
    cert_dir: Path

    # Network settings
    websocket_port: int = 9876
    discovery_enabled: bool = True

    # Sync settings
    sync_enabled: bool = True
    sync_text: bool = True
    sync_images: bool = True
    max_item_size: int = 10 * 1024 * 1024  # 10 MB

    # UI settings
    show_system_tray: bool = True
    start_minimized: bool = False


def get_app_dir() -> Path:
    """Get application data directory."""
    if os.name == "posix":
        if "darwin" in sys.platform:
            # macOS
            base = Path.home() / "Library" / "Application Support"
        else:
            # Linux
            base = Path(
                os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
            )
    else:
        # Windows (future support)
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))

    app_dir = base / "clibpard"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def load_config() -> AppConfig:
    """Load or create application configuration."""
    from clibpard.utils import generate_device_id
    import socket

    app_dir = get_app_dir()
    config_file = app_dir / "config.json"

    if config_file.exists():
        with open(config_file, "r") as f:
            data = json.load(f)
            data["data_dir"] = Path(data["data_dir"])
            data["db_path"] = Path(data["db_path"])
            data["cert_dir"] = Path(data["cert_dir"])
            return AppConfig(**data)

    # Create new config
    device_id = generate_device_id()
    device_name = socket.gethostname()

    cert_dir = app_dir / "certs"
    cert_dir.mkdir(exist_ok=True)

    config = AppConfig(
        device_id=device_id,
        device_name=device_name,
        data_dir=app_dir,
        db_path=app_dir / "clipboard.db",
        cert_dir=cert_dir,
    )

    save_config(config)
    return config


def save_config(config: AppConfig) -> None:
    """Save application configuration."""
    app_dir = get_app_dir()
    config_file = app_dir / "config.json"

    data = config.model_dump()
    data["data_dir"] = str(data["data_dir"])
    data["db_path"] = str(data["db_path"])
    data["cert_dir"] = str(data["cert_dir"])

    with open(config_file, "w") as f:
        json.dump(data, f, indent=2)
