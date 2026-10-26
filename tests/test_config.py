from __future__ import annotations

import unittest

from config import load_config
from core import SplitConfig


class FakeSetting:
    # Mirrors picard.config.ConfigSection: item access only, no .get().
    def __init__(self, values):
        self._values = values

    def __getitem__(self, name):
        return self._values.get(name)


class FakeGlobalConfig:
    def __init__(self, values=None):
        self.setting = FakeSetting(
            {'va_name': 'Various Artists'} if values is None else values
        )


class FakeApi:
    def __init__(self, values=None):
        self.global_config = FakeGlobalConfig(values)


class ConfigTests(unittest.TestCase):
    def test_uses_recommended_defaults(self):
        config = load_config(FakeApi())

        self.assertEqual(config, SplitConfig())
        self.assertTrue(config.multi_value)
        self.assertEqual(config.artist_tag_mode, 'all')
        self.assertEqual(config.album_artist_mode, 'all')
        self.assertFalse(config.collapse_albumartists)
        self.assertTrue(config.prefer_original_primary)
        self.assertTrue(config.split_existing)
        self.assertIn('Simon & Garfunkel', config.never_split)

    def test_va_name_is_read_from_global_settings(self):
        api = FakeApi({'va_name': 'Çeşitli Sanatçılar'})

        self.assertEqual(load_config(api).va_name, 'Çeşitli Sanatçılar')

    def test_missing_va_name_falls_back(self):
        self.assertEqual(load_config(FakeApi({})).va_name, 'Various Artists')

        class NoConfigApi:
            pass

        self.assertEqual(load_config(NoConfigApi()).va_name, 'Various Artists')


if __name__ == '__main__':
    unittest.main()
