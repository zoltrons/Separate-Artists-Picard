from __future__ import annotations

import unittest

from config import (
    OPTION_DEFAULTS,
    load_config,
    register_options,
)


class FakeConfigSection:
    def __init__(self):
        self.values = {}
        self.defaults = {}

    def register_option(self, name, default, **kwargs):
        self.defaults[name] = default
        self.values.setdefault(name, default)

    def get(self, name, default=None):
        return self.values.get(name, self.defaults.get(name, default))

    def __getitem__(self, name):
        return self.get(name)

    def __setitem__(self, name, value):
        self.values[name] = value


class FakeGlobalConfig:
    def __init__(self):
        self.setting = {'va_name': 'Various Artists'}


class FakeApi:
    def __init__(self):
        self.plugin_config = FakeConfigSection()
        self.global_config = FakeGlobalConfig()


class ConfigTests(unittest.TestCase):
    def test_defaults_are_registered_and_loaded(self):
        api = FakeApi()
        register_options(api)

        self.assertEqual(set(api.plugin_config.defaults), set(OPTION_DEFAULTS))
        config = load_config(api)

        self.assertEqual(config.separator, ', ')
        self.assertEqual(config.artist_tag_mode, 'all')
        self.assertEqual(config.album_artist_mode, 'all')
        self.assertFalse(config.collapse_albumartists)
        self.assertTrue(config.prefer_original_primary)
        self.assertTrue(config.split_existing)
        self.assertIn('Simon & Garfunkel', config.never_split)
        self.assertEqual(api.plugin_config['behavior_version'], 2)

    def test_multiline_settings(self):
        api = FakeApi()
        register_options(api)
        api.plugin_config['never_split'] = 'A & B\n\nC & D\nA & B\n'
        api.plugin_config['extra_separators'] = ' + \n\n×\n'
        api.plugin_config['artist_separator'] = ' / '

        config = load_config(api)

        self.assertEqual(config.never_split, ('A & B', 'C & D'))
        self.assertEqual(config.extra_separators, ('+', '×'))
        self.assertEqual(config.separator, ' / ')

    def test_old_collapse_default_is_migrated_once(self):
        api = FakeApi()
        register_options(api)
        api.plugin_config['album_artist_mode'] = 'first'
        api.plugin_config['collapse_albumartists'] = True

        config = load_config(api)

        self.assertEqual(config.album_artist_mode, 'all')
        self.assertFalse(config.collapse_albumartists)
        self.assertEqual(api.plugin_config['behavior_version'], 2)

        # After the migration an explicit choice is respected.
        api.plugin_config['album_artist_mode'] = 'first'
        api.plugin_config['collapse_albumartists'] = True
        config = load_config(api)

        self.assertEqual(config.album_artist_mode, 'first')
        self.assertTrue(config.collapse_albumartists)

    def test_invalid_modes_fall_back(self):
        api = FakeApi()
        register_options(api)
        api.plugin_config['artist_tag_mode'] = 'bogus'
        api.plugin_config['album_artist_mode'] = 'bogus'

        config = load_config(api)

        self.assertEqual(config.artist_tag_mode, 'all')
        self.assertEqual(config.album_artist_mode, 'all')

    def test_blank_separator_falls_back(self):
        api = FakeApi()
        register_options(api)
        api.plugin_config['artist_separator'] = '   '

        config = load_config(api)

        self.assertEqual(config.separator, ', ')


if __name__ == '__main__':
    unittest.main()
