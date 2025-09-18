""Helper functions for the application."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

import pytz
from pydantic import BaseModel

from ..config.settings import get_settings

T = TypeVar('T', bound=BaseModel)

def get_settings():
    ""Get application settings."""
    return get_settings()

def to_camel_case(string: str) -> str:
    ""Convert snake_case string to camelCase."""
    parts = string.split('_')
    return parts[0].lower() + ''.join(word.capitalize() for word in parts[1:])

def to_snake_case(string: str) -> str:
    ""Convert camelCase or PascalCase string to snake_case."""
    return ''.join(['_' + c.lower() if c.isupper() else c for c in string]).lstrip('_')

def parse_json(json_data: Union[str, bytes, bytearray]) -> Any:
    ""Parse JSON data with error handling."""
    try:
        return json.loads(json_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

def get_utc_now() -> datetime:
    ""Get current UTC time with timezone info."""
    return datetime.now(timezone.utc)

def localize_datetime(dt: datetime, timezone_str: str = "UTC") -> datetime:
    ""Localize a datetime object to the specified timezone."""
    tz = pytz.timezone(timezone_str)
    if dt.tzinfo is None:
        return tz.localize(dt)
    return dt.astimezone(tz)

def ensure_dir(directory: Union[str, Path]) -> Path:
    ""Ensure a directory exists, create it if it doesn't."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_env_file(env_file: Union[str, Path] = ".env") -> None:
    ""Load environment variables from a .env file."""
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value.strip('"\'')
    except FileNotFoundError:
        pass  # .env file is optional

def parse_model(data: Dict[str, Any], model: Type[T]) -> T:
    ""Parse a dictionary into a Pydantic model with error handling."""
    try:
        return model.parse_obj(data)
    except Exception as e:
        raise ValueError(f"Failed to parse model {model.__name__}: {e}") from e

def get_app_root() -> Path:
    ""Get the root directory of the application."""
    return Path(__file__).parent.parent.parent

def get_data_dir() -> Path:
    ""Get the data directory for the application."""
    data_dir = get_settings().DATA_DIR
    if not data_dir:
        data_dir = get_app_root() / "data"
    return ensure_dir(data_dir)

def get_temp_dir() -> Path:
    ""Get the temporary directory for the application."""
    temp_dir = get_settings().TEMP_DIR
    if not temp_dir:
        temp_dir = get_app_root() / "tmp"
    return ensure_dir(temp_dir)
