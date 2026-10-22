"""Configuration helpers shared by the plugin hooks and the options page."""

from __future__ import annotations

try:  # plugin package import (normal Picard loading)
    from .core import (
        DEFAULT_NEVER_SPLIT,
        SplitConfig,
    )
except ImportError:  # top-level import used by the test suite
    from core import (
        DEFAULT_NEVER_SPLIT,
        SplitConfig,
    )


CONFIG_VERSION = 2

OPTION_DEFAULTS = {
    'artist_separator': ', ',
    'artist_tag_mode': 'all',
    'album_artist_mode': 'all',
    'collapse_albumartists': False,
    'prefer_original_primary': True,
    'split_existing': True,
    'never_split': '\n'.join(DEFAULT_NEVER_SPLIT),
    'extra_separators': '',
    'behavior_version': 0,
}


def register_options(api) -> None:
    for name, default in OPTION_DEFAULTS.items():
        api.plugin_config.register_option(name, default)


def _lines(value) -> tuple[str, ...]:
    if isinstance(value, str):
        values = value.splitlines()
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        values = []
    result: list[str] = []
    for item in values:
        item = str(item).strip()
        if item and item not in result:
            result.append(item)
    return tuple(result)


def _config_version(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def load_config(api) -> SplitConfig:
    config = api.plugin_config
    try:
        va_name = api.global_config.setting.get('va_name', 'Various Artists')
    except (AttributeError, TypeError):
        va_name = 'Various Artists'

    # Version 1.0.0 defaulted to collapsing album artists.  Users upgrading
    # from that version get the new "preserve all album artists" default once;
    # after the behavior version is recorded, an explicit first-artist choice
    # is left untouched.
    if _config_version(config.get('behavior_version', 0)) < CONFIG_VERSION:
        if (
            config.get('album_artist_mode', 'all') == 'first'
            and bool(config.get('collapse_albumartists', False))
        ):
            config['album_artist_mode'] = 'all'
            config['collapse_albumartists'] = False
        config['behavior_version'] = CONFIG_VERSION

    return SplitConfig(
        separator=config.get('artist_separator', OPTION_DEFAULTS['artist_separator']),
        artist_tag_mode=config.get(
            'artist_tag_mode', OPTION_DEFAULTS['artist_tag_mode']
        ),
        album_artist_mode=config.get(
            'album_artist_mode', OPTION_DEFAULTS['album_artist_mode']
        ),
        collapse_albumartists=config.get(
            'collapse_albumartists', OPTION_DEFAULTS['collapse_albumartists']
        ),
        prefer_original_primary=config.get(
            'prefer_original_primary', OPTION_DEFAULTS['prefer_original_primary']
        ),
        split_existing=config.get(
            'split_existing', OPTION_DEFAULTS['split_existing']
        ),
        never_split=_lines(
            config.get('never_split', OPTION_DEFAULTS['never_split'])
        ),
        extra_separators=_lines(
            config.get('extra_separators', OPTION_DEFAULTS['extra_separators'])
        ),
        va_name=va_name or 'Various Artists',
    )
