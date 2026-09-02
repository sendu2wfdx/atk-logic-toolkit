"""Compatibility namespace for ATK Logic Toolkit 0.1/0.2 imports."""

from importlib import import_module
import sys

from atk_logic_toolkit import __version__

for _name in ("analysis", "capture", "cli", "decoders", "device", "hardware"):
    sys.modules[f"{__name__}.{_name}"] = import_module(f"atk_logic_toolkit.{_name}")

