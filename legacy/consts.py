from os import getenv
from pathlib import Path

_DEFAULT_CONFIG_PATH = "~/.shc-config.yml"
_DEFAULT_PLUGINS_PATH = "~/.shc-plugins"

CONFIG_PATH = Path(getenv("SHC_CONFIG_PATH", default=_DEFAULT_CONFIG_PATH)).expanduser()
PLUGINS_PATH = Path(getenv("SHC_PLUGINS_PATH", default=_DEFAULT_PLUGINS_PATH)).expanduser()
