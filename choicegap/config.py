"""Read explicitly supported local configuration without executing file contents."""
from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path, overwrite: bool = False) -> None:
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, separator, value = line.partition('=')
        key = key.strip()
        if separator and key in ('MODEL_API_KEY', 'META_MODEL'):
            if overwrite or key not in os.environ:
                os.environ[key] = value.strip().strip('"\'')
