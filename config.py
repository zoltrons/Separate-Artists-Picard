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
    'multi_value_artists': True,
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


def get_option(config, name: str):
    """Read a plugin option, falling back to its default.

    Picard's ``ConfigSection`` only supports item access (there is no
    ``.get()``); unregistered options read as ``None``.
    """

    try:
        value = config[name]
    except (KeyError, TypeError):
        value = None
    if value is None:
        return OPTION_DEFAULTS.get(name)
    return value


def _config_version(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def load_config(api) -> SplitConfig:
    config = api.plugin_config
    try:
        va_name = api.global_config.setting['va_name']
    except (AttributeError, KeyError, TypeError):
        va_name = 'Various Artists'

    # Version 1.0.0 defaulted to collapsing album artists.  Users upgrading
    # from that version get the new "preserve all album artists" default once;
    # after the behavior version is recorded, an explicit first-artist choice
    # is left untouched.
    if _config_version(get_option(config, 'behavior_version')) < CONFIG_VERSION:
        if (
            get_option(config, 'album_artist_mode') == 'first'
            and bool(get_option(config, 'collapse_albumartists'))
        ):
            config['album_artist_mode'] = 'all'
            config['collapse_albumartists'] = False
        config['behavior_version'] = CONFIG_VERSION

    return SplitConfig(
        separator=get_option(config, 'artist_separator'),
        multi_value=bool(get_option(config, 'multi_value_artists')),
        artist_tag_mode=get_option(config, 'artist_tag_mode'),
        album_artist_mode=get_option(config, 'album_artist_mode'),
        collapse_albumartists=get_option(config, 'collapse_albumartists'),
        prefer_original_primary=get_option(config, 'prefer_original_primary'),
        split_existing=get_option(config, 'split_existing'),
        never_split=_lines(
            get_option(config, 'never_split')
        ),
        extra_separators=_lines(
            get_option(config, 'extra_separators')
        ),
        va_name=va_name or 'Various Artists',
    )
