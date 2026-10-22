"""Core artist-splitting logic for the Separate Artists Picard plugin.

The module deliberately has no Picard or Qt imports.  That keeps the rules
easy to test and lets the plugin reuse the same code for automatic metadata
processing, manual actions and pre-save fixes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable, Sequence


VARIOUS_ARTISTS_ID = '89ad4ac3-39f7-470e-963a-56509c546377'

# These are real single artists whose names contain characters that look like
# artist separators.  MusicBrainz artist credits protect them automatically;
# this list protects them when we have to fall back to parsing a plain string.
DEFAULT_NEVER_SPLIT = (
    'AC/DC',
    'Blood, Sweat & Tears',
    'Bob Marley & The Wailers',
    'Brooks & Dunn',
    'Crosby, Stills & Nash',
    'Crosby, Stills, Nash & Young',
    'Dan + Shay',
    'Earth, Wind & Fire',
    'Florence + the Machine',
    'Hall & Oates',
    'Daryl Hall & John Oates',
    'Hootie & the Blowfish',
    'Kool & the Gang',
    'Mumford & Sons',
    'Of Mice & Men',
    'Sam & Dave',
    'Simon & Garfunkel',
    'Sly & the Family Stone',
    'The Mamas & the Papas',
    'Tyler, The Creator',
)

# Literal tokens.  The parser turns these into whitespace-aware regular
# expressions; a bare "&" or "/" is only a separator when it has whitespace on
# both sides, so names such as "AC/DC" and "R&B" stay intact.
DEFAULT_SEPARATORS = (
    '&',
    'feat.',
    'feat',
    'ft.',
    'ft',
    'featuring',
    'with',
    'x',
    '×',
    'vs.',
    'vs',
    '/',
    ';',
    ',',
)

_ALBUM_ARTIST_MODES = frozenset({'first', 'all', 'keep'})
_ARTIST_TAG_MODES = frozenset({'all', 'primary'})

_JOIN_TAIL_RE = re.compile(
    r'\s+(?:feat|ft|featuring|with|vs)\.?\s*$',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SplitConfig:
    """User-facing settings, with safe defaults."""

    separator: str = ', '
    artist_tag_mode: str = 'all'
    album_artist_mode: str = 'all'
    collapse_albumartists: bool = False
    prefer_original_primary: bool = True
    split_existing: bool = True
    never_split: tuple[str, ...] = DEFAULT_NEVER_SPLIT
    extra_separators: tuple[str, ...] = ()
    va_name: str = 'Various Artists'

    def __post_init__(self):
        separator = self.separator
        if not isinstance(separator, str) or not separator.strip():
            separator = ', '
        object.__setattr__(self, 'separator', separator)
        if self.artist_tag_mode not in _ARTIST_TAG_MODES:
            object.__setattr__(self, 'artist_tag_mode', 'all')
        if self.album_artist_mode not in _ALBUM_ARTIST_MODES:
            object.__setattr__(self, 'album_artist_mode', 'all')

    @property
    def separators(self) -> tuple[str, ...]:
        result: list[str] = []
        for token in DEFAULT_SEPARATORS + tuple(self.extra_separators):
            token = str(token).strip()
            if token and token not in result:
                result.append(token)
        return tuple(result)


@dataclass
class SplitResult:
    changed: bool = False
    artists: list[str] = field(default_factory=list)
    primary: str | None = None
    album_primary: str | None = None
    notes: list[str] = field(default_factory=list)


def _normalise(value: str) -> str:
    return re.sub(r'\s+', ' ', str(value)).strip()


def _key(value: str) -> str:
    return _normalise(value).casefold()


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = _normalise(value)
        if not value:
            continue
        key = _key(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _metadata_values(metadata, name: str) -> list[str]:
    if metadata is None:
        return []
    try:
        values = metadata.getall(name)
    except (AttributeError, TypeError):
        value = metadata.get(name, '') if hasattr(metadata, 'get') else ''
        if not value:
            return []
        return [str(value)]
    return [str(value) for value in values if str(value).strip()]


def _separator_pattern(token: str) -> str:
    token = token.strip()
    escaped = re.escape(token)

    if token == '&':
        return r'\s+&\s+'
    if token == '/':
        return r'\s+/\s+'
    if token == ';':
        return r'\s*;\s*'
    if token == ',':
        # Protect "Tyler, The Creator" and similar names.
        return r',\s+(?!(?:the|a|an)\s)'
    if token in {'feat', 'ft'}:
        return r'\s+' + re.escape(token) + r'\.?\s+'
    if token in {'vs', 'vs.'}:
        return r'\s+vs\.?\s+'
    return r'\s+' + escaped + r'\s+'


def _clean_part(part: str) -> str:
    part = _normalise(part)
    part = part.strip(' \t\r\n,;&/')
    part = _JOIN_TAIL_RE.sub('', part)
    return part.strip()


def is_never_split(value: str, never_split: Sequence[str]) -> bool:
    key = _key(value)
    return any(key == _key(item) for item in never_split)


def split_artist_string(
    value: str,
    separators: Sequence[str] = DEFAULT_SEPARATORS,
    never_split: Sequence[str] = DEFAULT_NEVER_SPLIT,
) -> list[str]:
    """Split a display artist string into individual artist names.

    The function is conservative: if the whole value is a known single artist,
    or if no separator is present, the original string is returned unchanged.
    """

    value = _normalise(value)
    if not value:
        return []
    if is_never_split(value, never_split):
        return [value]

    parts = [value]
    for token in sorted({str(s).strip() for s in separators if str(s).strip()}, key=len, reverse=True):
        pattern = _separator_pattern(token)
        new_parts: list[str] = []
        for part in parts:
            new_parts.extend(re.split(pattern, part, flags=re.IGNORECASE))
        parts = new_parts

    cleaned = _unique(_clean_part(part) for part in parts)
    if len(cleaned) <= 1:
        return [value]
    return cleaned


def extract_artist_names(metadata, config: SplitConfig) -> list[str]:
    """Return the individual track artists from Picard metadata.

    Picard's ``artists`` tag is the authoritative multi-value list produced
    from MusicBrainz artist credits.  When it is absent (for example for a
    manually tagged file) the plain ``artist`` string is parsed.
    """

    artists = _unique(_metadata_values(metadata, 'artists'))
    artist_values = _unique(_metadata_values(metadata, 'artist'))
    raw_artist = artist_values[0] if artist_values else ''

    if len(artists) >= 2:
        return artists
    if len(artist_values) >= 2:
        return artist_values
    if len(artists) == 1:
        # A single MusicBrainz credit is authoritative.  This is what keeps
        # "Simon & Garfunkel", "AC/DC" and "Tyler, The Creator" intact.
        if not raw_artist or _key(artists[0]) == _key(raw_artist):
            return artists
    if not raw_artist:
        return artists

    if config.split_existing:
        parsed = split_artist_string(
            raw_artist,
            separators=config.separators,
            never_split=config.never_split,
        )
        if len(parsed) >= 2:
            return parsed
    return [raw_artist]


def extract_album_artist_names(metadata, config: SplitConfig) -> list[str]:
    """Return the individual album artists from Picard metadata."""

    album_artists = _unique(_metadata_values(metadata, 'albumartists'))
    album_artist_values = _unique(_metadata_values(metadata, 'albumartist'))
    raw_album_artist = album_artist_values[0] if album_artist_values else ''

    if album_artists:
        return album_artists
    if len(album_artist_values) >= 2:
        return album_artist_values
    if not raw_album_artist:
        return []
    if config.split_existing:
        parsed = split_artist_string(
            raw_album_artist,
            separators=config.separators,
            never_split=config.never_split,
        )
        if len(parsed) >= 2:
            return parsed
    return [raw_album_artist]


def extract_original_names(metadata, config: SplitConfig) -> list[str]:
    """Return the artist order already present in the file.

    The singular ARTIST/ALBUMARTIST string is the value a user (or a Spotify
    downloader) normally sees, so it is preferred over the plural tag when
    deciding which artist should be primary.  The plural tag is still used as
    a fallback when the singular value does not name a known artist.
    """

    values = _unique(_metadata_values(metadata, 'artist'))
    if values:
        parsed = split_artist_string(
            values[0],
            separators=config.separators,
            never_split=config.never_split,
        )
        plural = _unique(_metadata_values(metadata, 'artists'))
        if len(parsed) >= 2:
            return parsed
        if parsed and any(_key(parsed[0]) == _key(item) for item in plural):
            return parsed
        if len(plural) > 1:
            return plural
        if parsed:
            return parsed
    return extract_artist_names(metadata, config)


def extract_original_album_artist_names(metadata, config: SplitConfig) -> list[str]:
    """Album-artist equivalent of :func:`extract_original_names`."""

    values = _unique(_metadata_values(metadata, 'albumartist'))
    if values:
        parsed = split_artist_string(
            values[0],
            separators=config.separators,
            never_split=config.never_split,
        )
        plural = _unique(_metadata_values(metadata, 'albumartists'))
        if len(parsed) >= 2:
            return parsed
        if parsed and any(_key(parsed[0]) == _key(item) for item in plural):
            return parsed
        if len(plural) > 1:
            return plural
        if parsed:
            return parsed
    return extract_album_artist_names(metadata, config)


def _match_index(name: str, names: Sequence[str]) -> int | None:
    wanted = _key(name)
    for index, candidate in enumerate(names):
        if _key(candidate) == wanted:
            return index
    return None


def _expand_single_name(
    current_name: str,
    original_names: Sequence[str],
    config: SplitConfig,
) -> list[str] | None:
    """Split a single combined MusicBrainz credit using the file's own order.

    Some collaborations are stored as one MusicBrainz artist entity even
    though the source file (for example a Spotify download) lists the artists
    separately.  This is only done when every name from the existing file is
    also present in the combined credit, and never for names on the
    never-split list.
    """

    if not original_names or is_never_split(current_name, config.never_split):
        return None
    parts = split_artist_string(
        current_name,
        separators=config.separators,
        never_split=config.never_split,
    )
    if len(parts) < 2:
        return None
    part_keys = {_key(part) for part in parts}
    if not all(_key(name) in part_keys for name in original_names):
        return None
    return reorder_by_original(parts, original_names)


def _reorder_order(current: Sequence[str], original: Sequence[str]) -> list[int] | None:
    """Return the index permutation that moves the original first artist up."""

    if not current or not original:
        return None
    index = _match_index(original[0], current)
    if index is None or index == 0:
        return None
    return [index, *range(index), *range(index + 1, len(current))]


def _apply_order(values: Sequence[str], order: Sequence[int]) -> list[str]:
    return [values[index] for index in order]


def reorder_by_original(current: Sequence[str], original: Sequence[str]) -> list[str]:
    """Move the original first artist to the front when it is in ``current``."""

    order = _reorder_order(current, original)
    return _apply_order(current, order) if order else list(current)


def is_various_artists(metadata, config: SplitConfig) -> bool:
    ids = _metadata_values(metadata, 'musicbrainz_albumartistid')
    if VARIOUS_ARTISTS_ID in ids:
        return True
    names = extract_album_artist_names(metadata, config)
    if not names:
        names = _metadata_values(metadata, 'albumartist')
    va_name = _key(config.va_name or 'Various Artists')
    return any(_key(name) == va_name for name in names)


def _set_value(metadata, tag: str, value) -> bool:
    if isinstance(value, (list, tuple)):
        values = list(value)
        if metadata.getall(tag) != values:
            metadata[tag] = values
            return True
        return False
    if metadata.get(tag) != value:
        metadata[tag] = value
        return True
    return False


def _set_joined_sort(
    metadata,
    singular_tag: str,
    plural_tag: str,
    separator: str,
    order: Sequence[int] | None = None,
) -> bool:
    """Write all sort names, preserving multi-artist order."""

    sort_names = _metadata_values(metadata, '~' + plural_tag + '_sort')
    if not sort_names:
        return False
    if order:
        if len(sort_names) != len(order):
            return False
        sort_names = _apply_order(sort_names, order)
    return _set_value(metadata, singular_tag, separator.join(sort_names))


def _sort_name_for(metadata, primary: str, plural_tag: str) -> str | None:
    names = _metadata_values(metadata, plural_tag)
    if not names:
        return None
    for index, name in enumerate(names):
        if _key(name) != _key(primary):
            continue
        sort_names = _metadata_values(metadata, '~' + plural_tag + '_sort')
        if index < len(sort_names) and sort_names[index].strip():
            return sort_names[index].strip()
        return None
    return None


def apply_split(
    metadata,
    config: SplitConfig | None = None,
    original_metadata=None,
) -> SplitResult:
    """Apply the split rules to a Picard ``Metadata``-like object.

    ``original_metadata`` is optional.  When given (and enabled in the
    settings), its first artist is preferred as the primary track artist.
    This is how a Spotify-derived artist order is preserved without calling
    Spotify: the order already present in the file wins, as long as the name
    also appears in the MusicBrainz credit.

    Album credits are different: a multi-artist album keeps every album
    artist by default.  Only ``album_artist_mode='first'`` collapses it.
    """

    config = config or SplitConfig()
    result = SplitResult()

    artists = extract_artist_names(metadata, config)
    if not artists:
        return result

    artist_order = None
    if original_metadata is not None and config.prefer_original_primary:
        original_artists = extract_original_names(original_metadata, config)
        if len(artists) == 1 and config.split_existing:
            expanded = _expand_single_name(artists[0], original_artists, config)
            if expanded:
                result.notes.append(
                    f"single credit {artists[0]!r} expanded to {expanded!r}"
                )
                artists = expanded
        order = _reorder_order(artists, original_artists)
        if order:
            artist_order = order
            artists_before = list(artists)
            artists = _apply_order(artists, order)
            result.notes.append(
                f"primary artist reordered from {artists_before[0]!r} to {artists[0]!r}"
            )
            ids = _metadata_values(metadata, 'musicbrainz_artistid')
            if len(ids) == len(artists_before):
                if _set_value(
                    metadata, 'musicbrainz_artistid', _apply_order(ids, order)
                ):
                    result.notes.append('musicbrainz_artistid reordered')
                    result.changed = True

    result.artists = artists
    result.primary = artists[0]

    # ARTIST: singular display tag.  "A, B" is what Navidrome and most
    # players show; "A" is available for scrobblers that only read ARTIST.
    if config.artist_tag_mode == 'primary':
        display_artist = result.primary
    elif len(artists) >= 2:
        display_artist = config.separator.join(artists)
    else:
        display_artist = metadata.get('artist') or result.primary

    if display_artist and _set_value(metadata, 'artist', display_artist):
        result.notes.append(f"artist set to {display_artist!r}")
        result.changed = True

    # ARTISTS: real multi-value tag used by Navidrome and modern players.
    if len(artists) >= 2 and _set_value(metadata, 'artists', artists):
        result.notes.append('multi-value artists tag updated')
        result.changed = True

    # Keep the sort tag consistent with the chosen ARTIST display mode.
    if len(artists) >= 2:
        if config.artist_tag_mode == 'primary':
            sort_name = _sort_name_for(metadata, result.primary, 'artists')
            if sort_name and _set_value(metadata, 'artistsort', sort_name):
                result.notes.append(f"artistsort set to {sort_name!r}")
                result.changed = True
        elif _set_joined_sort(
            metadata, 'artistsort', 'artists', config.separator, artist_order
        ):
            result.notes.append('artistsort updated for all artists')
            result.changed = True

    if config.album_artist_mode == 'keep' or is_various_artists(metadata, config):
        return result

    album_artists = extract_album_artist_names(metadata, config)
    if not album_artists:
        return result

    album_order = None
    if original_metadata is not None and config.prefer_original_primary:
        original_album_artists = extract_original_album_artist_names(
            original_metadata, config
        )
        if len(album_artists) == 1 and config.split_existing:
            expanded = _expand_single_name(
                album_artists[0], original_album_artists, config
            )
            if expanded:
                result.notes.append(
                    f"single album credit {album_artists[0]!r} expanded to {expanded!r}"
                )
                album_artists = expanded
        album_order = _reorder_order(album_artists, original_album_artists)
        if album_order:
            album_artists_before = list(album_artists)
            album_artists = _apply_order(album_artists, album_order)
            result.notes.append(
                f"album artist reordered from {album_artists_before[0]!r} "
                f"to {album_artists[0]!r}"
            )

    result.album_primary = album_artists[0]
    album_ids = _metadata_values(metadata, 'musicbrainz_albumartistid')
    album_ids_are_aligned = len(album_ids) == len(album_artists)

    if config.album_artist_mode == 'all':
        display_album_artist = config.separator.join(album_artists)
        plural_album_artists = album_artists
    else:
        display_album_artist = result.album_primary
        plural_album_artists = (
            [result.album_primary] if config.collapse_albumartists else album_artists
        )

    if _set_value(metadata, 'albumartist', display_album_artist):
        result.notes.append(f"albumartist set to {display_album_artist!r}")
        result.changed = True
    if _set_value(metadata, 'albumartists', plural_album_artists):
        result.notes.append('multi-value albumartists tag updated')
        result.changed = True

    # Collapse the MusicBrainz album artist IDs to the chosen primary artist
    # so the identifier tags agree with the singular album artist.
    if album_ids and album_ids[0] != '':
        if album_order and album_ids_are_aligned:
            album_ids = _apply_order(album_ids, album_order)
            note = 'musicbrainz_albumartistid reordered'
        else:
            note = ''
        if (
            config.album_artist_mode == 'first'
            and config.collapse_albumartists
            and album_ids_are_aligned
        ):
            album_ids = [album_ids[0]]
            note = 'musicbrainz_albumartistid collapsed to primary'
        if note and _set_value(metadata, 'musicbrainz_albumartistid', album_ids):
            result.notes.append(note)
            result.changed = True

    if config.album_artist_mode == 'first':
        sort_name = _sort_name_for(
            metadata, result.album_primary, 'albumartists'
        )
        if sort_name and _set_value(metadata, 'albumartistsort', sort_name):
            result.notes.append(f"albumartistsort set to {sort_name!r}")
            result.changed = True
    elif _set_joined_sort(
        metadata, 'albumartistsort', 'albumartists', config.separator, album_order
    ):
        result.notes.append('albumartistsort updated for all album artists')
        result.changed = True

    return result
