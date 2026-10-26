"""Zero-configuration settings for the Separate Artists plugin.

The plugin has no options of its own: it always uses the recommended
``SplitConfig`` defaults.  Only Picard's own "Various Artists" name is read,
so compilations are recognised in the user's language.
"""

from __future__ import annotations

try:  # plugin package import (normal Picard loading)
    from .core import SplitConfig
except ImportError:  # top-level import used by the test suite
    from core import SplitConfig


DEFAULT_VA_NAME = 'Various Artists'


def load_config(api) -> SplitConfig:
    # Picard's ConfigSection only supports item access (there is no .get()).
    try:
        va_name = api.global_config.setting['va_name']
    except (AttributeError, KeyError, TypeError):
        va_name = None
    return SplitConfig(va_name=va_name or DEFAULT_VA_NAME)
