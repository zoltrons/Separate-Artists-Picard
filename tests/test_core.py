from __future__ import annotations

import unittest

from core import (
    SplitConfig,
    VARIOUS_ARTISTS_ID,
    apply_split,
    split_artist_string,
)


class FakeMetadata:
    """Small stand-in for picard.metadata.Metadata."""

    def __init__(self, **tags):
        self._store: dict[str, list[str]] = {}
        for name, value in tags.items():
            self[name] = value

    def getall(self, name):
        return list(self._store.get(name, ()))

    def get(self, name, default=None):
        values = self._store.get(name)
        if not values:
            return default
        return '; '.join(values)

    def __getitem__(self, name):
        return self.get(name) or ''

    def __setitem__(self, name, values):
        if isinstance(values, str):
            values = [values]
        cleaned = [str(value) for value in values if str(value)]
        if cleaned:
            self._store[name] = cleaned
        else:
            self._store.pop(name, None)

    def __contains__(self, name):
        return name in self._store

    def delete(self, name):
        self._store.pop(name, None)

    def dump(self):
        return {key: list(value) for key, value in self._store.items()}


class SplitArtistStringTests(unittest.TestCase):
    def test_ampersand(self):
        self.assertEqual(split_artist_string('A & B'), ['A', 'B'])

    def test_feat_and_ampersand(self):
        self.assertEqual(
            split_artist_string('A feat. B & C'), ['A', 'B', 'C']
        )

    def test_comma(self):
        self.assertEqual(split_artist_string('A, B'), ['A', 'B'])

    def test_tyler_the_creator_is_not_split(self):
        self.assertEqual(
            split_artist_string('Tyler, The Creator'), ['Tyler, The Creator']
        )

    def test_known_group_is_not_split(self):
        self.assertEqual(
            split_artist_string('Simon & Garfunkel'), ['Simon & Garfunkel']
        )
        self.assertEqual(
            split_artist_string('Earth, Wind & Fire'), ['Earth, Wind & Fire']
        )
        self.assertEqual(
            split_artist_string('Blood, Sweat & Tears'), ['Blood, Sweat & Tears']
        )

    def test_slash_requires_spaces(self):
        self.assertEqual(split_artist_string('AC/DC'), ['AC/DC'])
        self.assertEqual(split_artist_string('A / B'), ['A', 'B'])

    def test_semicolon(self):
        self.assertEqual(split_artist_string('A; B'), ['A', 'B'])

    def test_custom_separator(self):
        self.assertEqual(
            split_artist_string('A + B', separators=('+',)), ['A', 'B']
        )

    def test_empty(self):
        self.assertEqual(split_artist_string(''), [])


class ApplySplitTests(unittest.TestCase):
    def test_ampersand_split_with_mb_credit(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
            musicbrainz_albumartistid=['id-a', 'id-b'],
        )

        result = apply_split(metadata)

        self.assertTrue(result.changed)
        self.assertEqual(metadata.getall('artist'), ['A', 'B'])
        self.assertEqual(metadata.getall('artists'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartist'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartists'), ['A', 'B'])
        self.assertEqual(
            metadata.getall('musicbrainz_albumartistid'), ['id-a', 'id-b']
        )
        self.assertEqual(result.primary, 'A')
        self.assertEqual(result.album_primary, 'A')

    def test_first_artist_mode_collapses_album(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
            musicbrainz_albumartistid=['id-a', 'id-b'],
        )

        result = apply_split(
            metadata,
            SplitConfig(
                album_artist_mode='first', collapse_albumartists=True
            ),
        )

        self.assertEqual(metadata['albumartist'], 'A')
        self.assertEqual(metadata.getall('albumartists'), ['A'])
        self.assertEqual(
            metadata.getall('musicbrainz_albumartistid'), ['id-a']
        )
        self.assertEqual(result.album_primary, 'A')

    def test_single_mb_artist_is_authoritative(self):
        metadata = FakeMetadata(
            artist='Simon & Garfunkel',
            artists=['Simon & Garfunkel'],
            albumartist='Simon & Garfunkel',
            albumartists=['Simon & Garfunkel'],
        )

        result = apply_split(metadata)

        self.assertFalse(result.changed)
        self.assertEqual(metadata['artist'], 'Simon & Garfunkel')
        self.assertEqual(metadata['albumartist'], 'Simon & Garfunkel')

    def test_tyler_the_creator_is_not_split(self):
        metadata = FakeMetadata(artist='Tyler, The Creator')

        result = apply_split(metadata)

        self.assertFalse(result.changed)
        self.assertEqual(metadata['artist'], 'Tyler, The Creator')

    def test_fallback_feat_and_ampersand(self):
        metadata = FakeMetadata(artist='A feat. B & C')

        result = apply_split(metadata)

        self.assertTrue(result.changed)
        self.assertEqual(metadata.getall('artist'), ['A', 'B', 'C'])
        self.assertEqual(metadata.getall('artists'), ['A', 'B', 'C'])

    def test_various_artists_album_is_kept(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='Various Artists',
            albumartists=['Various Artists'],
            musicbrainz_albumartistid=[VARIOUS_ARTISTS_ID],
        )

        result = apply_split(metadata)

        self.assertTrue(result.changed)
        self.assertEqual(metadata.getall('artist'), ['A', 'B'])
        self.assertEqual(metadata['albumartist'], 'Various Artists')
        self.assertEqual(metadata.getall('albumartists'), ['Various Artists'])
        self.assertEqual(
            metadata.getall('musicbrainz_albumartistid'), [VARIOUS_ARTISTS_ID]
        )

    def test_original_spotify_order_wins(self):
        metadata = FakeMetadata(
            artist='B & A',
            artists=['B', 'A'],
            albumartist='B & A',
            albumartists=['B', 'A'],
        )
        original = FakeMetadata(
            artist='A, B',
            artists=['A', 'B'],
            albumartist='A',
            albumartists=['A'],
        )

        result = apply_split(metadata, original_metadata=original)

        self.assertEqual(metadata.getall('artist'), ['A', 'B'])
        self.assertEqual(metadata.getall('artists'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartist'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartists'), ['A', 'B'])
        self.assertEqual(result.primary, 'A')

    def test_single_mb_credit_expands_from_original(self):
        metadata = FakeMetadata(artist='A & B', artists=['A & B'])
        original = FakeMetadata(artist='A, B')

        apply_split(metadata, original_metadata=original)

        self.assertEqual(metadata.getall('artist'), ['A', 'B'])
        self.assertEqual(metadata.getall('artists'), ['A', 'B'])

    def test_single_mb_credit_uses_original_primary(self):
        metadata = FakeMetadata(artist='A & B', artists=['A & B'])
        original = FakeMetadata(artist='B')

        apply_split(metadata, original_metadata=original)

        self.assertEqual(metadata.getall('artist'), ['B', 'A'])
        self.assertEqual(metadata.getall('artists'), ['B', 'A'])

    def test_known_group_is_not_expanded(self):
        metadata = FakeMetadata(
            artist='Simon & Garfunkel', artists=['Simon & Garfunkel']
        )
        original = FakeMetadata(artist='Simon & Garfunkel')

        result = apply_split(metadata, original_metadata=original)

        self.assertFalse(result.changed)
        self.assertEqual(metadata['artist'], 'Simon & Garfunkel')

    def test_single_album_credit_expands_from_original(self):
        metadata = FakeMetadata(
            artist='C',
            artists=['C'],
            albumartist='A & B',
            albumartists=['A & B'],
        )
        original = FakeMetadata(albumartist='B')

        apply_split(metadata, original_metadata=original)

        self.assertEqual(metadata.getall('albumartist'), ['B', 'A'])
        self.assertEqual(metadata.getall('albumartists'), ['B', 'A'])

    def test_single_album_credit_uses_original_primary_in_first_mode(self):
        metadata = FakeMetadata(
            artist='C',
            artists=['C'],
            albumartist='A & B',
            albumartists=['A & B'],
        )
        original = FakeMetadata(albumartist='B')

        apply_split(
            metadata,
            SplitConfig(
                album_artist_mode='first', collapse_albumartists=True
            ),
            original_metadata=original,
        )

        self.assertEqual(metadata['albumartist'], 'B')
        self.assertEqual(metadata.getall('albumartists'), ['B'])

    def test_original_joined_plural_still_uses_singular_order(self):
        metadata = FakeMetadata(artist='B & A', artists=['B', 'A'])
        original = FakeMetadata(artist='A & B', artists=['A & B'])

        apply_split(metadata, original_metadata=original)

        self.assertEqual(metadata.getall('artist'), ['A', 'B'])
        self.assertEqual(metadata.getall('artists'), ['A', 'B'])

    def test_original_primary_only_singular_wins(self):
        metadata = FakeMetadata(artist='A & B', artists=['A', 'B'])
        original = FakeMetadata(artist='B', artists=['A', 'B'])

        apply_split(metadata, original_metadata=original)

        self.assertEqual(metadata.getall('artist'), ['B', 'A'])
        self.assertEqual(metadata.getall('artists'), ['B', 'A'])

    def test_original_order_can_be_disabled(self):
        metadata = FakeMetadata(artist='B & A', artists=['B', 'A'])
        original = FakeMetadata(artist='A, B')

        apply_split(
            metadata,
            SplitConfig(prefer_original_primary=False),
            original_metadata=original,
        )

        self.assertEqual(metadata.getall('artist'), ['B', 'A'])

    def test_idempotent(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )

        first = apply_split(metadata)
        second = apply_split(metadata)

        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertEqual(metadata.getall('artist'), ['A', 'B'])

    def test_album_artists_all_mode(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )

        apply_split(metadata, SplitConfig(album_artist_mode='all'))

        self.assertEqual(metadata.getall('albumartist'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartists'), ['A', 'B'])

    def test_album_artist_keep_mode(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )

        apply_split(metadata, SplitConfig(album_artist_mode='keep'))

        self.assertEqual(metadata.getall('artist'), ['A', 'B'])
        self.assertEqual(metadata['albumartist'], 'A & B')
        self.assertEqual(metadata.getall('albumartists'), ['A', 'B'])

    def test_primary_only_artist_tag(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )

        apply_split(metadata, SplitConfig(artist_tag_mode='primary'))

        self.assertEqual(metadata['artist'], 'A')
        self.assertEqual(metadata.getall('artists'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartist'), ['A', 'B'])

    def test_single_track_artist_with_collaboration_album(self):
        metadata = FakeMetadata(
            artist='C',
            artists=['C'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )

        apply_split(metadata)

        self.assertEqual(metadata['artist'], 'C')
        self.assertEqual(metadata.getall('albumartist'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartists'), ['A', 'B'])

    def test_single_track_artist_with_first_artist_album_mode(self):
        metadata = FakeMetadata(
            artist='C',
            artists=['C'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )

        apply_split(
            metadata,
            SplitConfig(
                album_artist_mode='first', collapse_albumartists=True
            ),
        )

        self.assertEqual(metadata['artist'], 'C')
        self.assertEqual(metadata['albumartist'], 'A')
        self.assertEqual(metadata.getall('albumartists'), ['A'])

    def test_empty_metadata(self):
        metadata = FakeMetadata()

        result = apply_split(metadata)

        self.assertFalse(result.changed)
        self.assertEqual(metadata.dump(), {})

    def test_custom_never_split(self):
        metadata = FakeMetadata(artist='A & B')

        result = apply_split(
            metadata,
            SplitConfig(never_split=('A & B',)),
        )

        self.assertFalse(result.changed)
        self.assertEqual(metadata['artist'], 'A & B')

    def test_extra_separator_and_custom_display(self):
        metadata = FakeMetadata(artist='A + B')

        apply_split(
            metadata,
            SplitConfig(
                separator=' / ', multi_value=False, extra_separators=('+',)
            ),
        )

        self.assertEqual(metadata.getall('artist'), ['A / B'])
        self.assertEqual(metadata.getall('artists'), ['A', 'B'])

    def test_no_album_tags(self):
        metadata = FakeMetadata(artist='A & B')

        apply_split(metadata)

        self.assertEqual(metadata.getall('artist'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartist'), [])

    def test_musicbrainz_ids_follow_reorder(self):
        metadata = FakeMetadata(
            artist='B & A',
            artists=['B', 'A'],
            musicbrainz_artistid=['id-b', 'id-a'],
            albumartist='B & A',
            albumartists=['B', 'A'],
            musicbrainz_albumartistid=['album-b', 'album-a'],
        )
        original = FakeMetadata(artist='A, B', albumartist='A')

        apply_split(metadata, original_metadata=original)

        self.assertEqual(
            metadata.getall('musicbrainz_artistid'), ['id-a', 'id-b']
        )
        self.assertEqual(
            metadata.getall('musicbrainz_albumartistid'),
            ['album-a', 'album-b'],
        )

    def test_album_ids_collapsed_in_first_mode(self):
        metadata = FakeMetadata(
            artist='B & A',
            artists=['B', 'A'],
            musicbrainz_artistid=['id-b', 'id-a'],
            albumartist='B & A',
            albumartists=['B', 'A'],
            musicbrainz_albumartistid=['album-b', 'album-a'],
        )
        original = FakeMetadata(artist='A, B', albumartist='A')

        apply_split(
            metadata,
            SplitConfig(
                album_artist_mode='first', collapse_albumartists=True
            ),
            original_metadata=original,
        )

        self.assertEqual(
            metadata.getall('musicbrainz_albumartistid'), ['album-a']
        )

    def test_album_ids_reordered_in_all_mode(self):
        metadata = FakeMetadata(
            artist='B & A',
            artists=['B', 'A'],
            albumartist='B & A',
            albumartists=['B', 'A'],
            musicbrainz_albumartistid=['album-b', 'album-a'],
        )
        original = FakeMetadata(albumartist='A')

        apply_split(
            metadata,
            SplitConfig(album_artist_mode='all'),
            original_metadata=original,
        )

        self.assertEqual(
            metadata.getall('musicbrainz_albumartistid'),
            ['album-a', 'album-b'],
        )

    def test_sort_names_keep_all_artists(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )
        metadata['~artists_sort'] = ['A, The', 'B']
        metadata['~albumartists_sort'] = ['A, The', 'B']

        apply_split(metadata)

        self.assertEqual(metadata.getall('artistsort'), ['A, The', 'B'])
        self.assertEqual(metadata.getall('albumartistsort'), ['A, The', 'B'])

    def test_joined_mode_writes_single_strings(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )
        metadata['~artists_sort'] = ['A, The', 'B']

        apply_split(metadata, SplitConfig(separator=';', multi_value=False))

        self.assertEqual(metadata.getall('artist'), ['A;B'])
        self.assertEqual(metadata.getall('albumartist'), ['A;B'])
        self.assertEqual(metadata.getall('artistsort'), ['A, The;B'])
        self.assertEqual(metadata.getall('artists'), ['A', 'B'])

    def test_sort_names_follow_primary_in_first_mode(self):
        metadata = FakeMetadata(
            artist='A & B',
            artists=['A', 'B'],
            albumartist='A & B',
            albumartists=['A', 'B'],
        )
        metadata['~artists_sort'] = ['A, The', 'B']
        metadata['~albumartists_sort'] = ['A, The', 'B']

        apply_split(
            metadata,
            SplitConfig(
                artist_tag_mode='primary',
                album_artist_mode='first',
                collapse_albumartists=True,
            ),
        )

        self.assertEqual(metadata['artistsort'], 'A, The')
        self.assertEqual(metadata['albumartistsort'], 'A, The')

    def test_album_artist_reordered_from_original(self):
        metadata = FakeMetadata(
            artist='B & A',
            artists=['B', 'A'],
            albumartist='B & A',
            albumartists=['B', 'A'],
        )
        original = FakeMetadata(albumartist='A')

        apply_split(metadata, original_metadata=original)

        self.assertEqual(metadata.getall('albumartist'), ['A', 'B'])
        self.assertEqual(metadata.getall('albumartists'), ['A', 'B'])


if __name__ == '__main__':
    unittest.main()
