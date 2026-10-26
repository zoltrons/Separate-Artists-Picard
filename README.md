# Separate Artists

A MusicBrainz Picard 3 plugin that writes multi-artist credits as separate
artist tags, while keeping multi-artist albums intact.

For a track credited to **A & B** it writes:

```text
ARTIST       = A; B        (multi-value)
ARTISTS      = A; B        (multi-value)
ALBUMARTIST  = A; B        (multi-value)
ALBUMARTISTS = A; B        (multi-value)
```

Every tag holds one value per artist, so Navidrome and similar players link
each artist separately. A joined `ARTIST = A, B` string is still available as
an option.

A single-artist album stays single (`ALBUMARTIST = A`,
`ALBUMARTISTS = A`). Multi-artist albums are never reduced to the first
artist unless the optional first-artist mode is selected.

## Features

- Splits joined credits such as `A & B`, `A feat. B`, and `A, B`.
- Writes the singular display tags and the multi-value
  `ARTISTS`/`ALBUMARTISTS` tags.
- Keeps every album artist on collaboration albums.
- Uses MusicBrainz artist credits as the source of truth.
- Does not split genuine names such as Simon & Garfunkel, AC/DC,
  Tyler, The Creator, or Earth, Wind & Fire.
- Keeps a Spotify-style artist order that is already present in the file
  when the names match the MusicBrainz credit.
- Adds a right-click action for tracks, files, albums, and clusters.
- Leaves Various Artists compilations unchanged.

## Tags written

| Tag | Multi-artist example | Purpose |
| --- | --- | --- |
| `ARTIST` | `A; B` (multi-value) | Display artist |
| `ARTISTS` | `A; B` | Individual track artists |
| `ALBUMARTIST` | `A; B` (multi-value) | All album artists |
| `ALBUMARTISTS` | `A; B` | Individual album artists |

The first track artist is treated as the primary artist. This lets
scrobblers that submit only the first artist report the track under **A**
instead of the collaboration name **A & B**.

## Installation

### From Picard

1. Open **Options → Plugins**.
2. Click **Install Plugin…**.
3. Open the **URL** tab and paste this repository's Git URL.
4. Install and enable **Separate Artists**.

Picard's plugin manager handles the repository checkout and module naming.

### Manual installation

Clone the repository into a folder named `separate_artists`, then install it
from Picard's **Local** tab:

```bash
git clone <repository-url> separate_artists
```

Alternatively, extract a release archive or copy the plugin directory into
Picard's v3 plugin folder:

```text
macOS:   ~/Library/Application Support/MusicBrainz/Picard/plugins3/
Linux:   ~/.local/share/MusicBrainz/Picard/plugins3/
Windows: %LOCALAPPDATA%\MusicBrainz\Picard\plugins3\
```

The folder must contain `MANIFEST.toml` and `__init__.py`. Restart Picard and
enable the plugin.

## Settings

**Options → Plugins → Separate Artists**

| Setting | Default | Description |
| --- | --- | --- |
| Multiple values | on | Writes `ARTIST`/`ALBUMARTIST` (and their sort tags) with one value per artist. |
| Display separator | `, ` | Only used when multiple values are off: joins `ARTIST` and a multi-artist `ALBUMARTIST` into one string. |
| ARTIST tag | all artists | Write all artists, or only the primary artist. `ARTISTS` is written either way. |
| ALBUMARTIST/ALBUMARTISTS | Preserve all | Keep every album artist. `First artist only` collapses the album to one artist. `Leave unchanged` skips album tags. |
| Collapse ALBUMARTISTS | Off | Only used by first-artist mode. Off keeps every album artist. |
| Use the file's existing first artist | On | Preserve Spotify-style primary order when it matches the MusicBrainz credit. |
| Split plain artist strings | On | Fallback for files without a multi-value MusicBrainz credit. |
| Extra separators | empty | Additional separator tokens, one per line. |
| Never split | common group names | Names that the string fallback must never split, one per line. |

## Scrobbling

Last.fm does not support multiple artists in one scrobble. If the player sends
the raw tag `A & B`, the scrobble is attributed to an artist called
**A & B** instead of **A**.

For Navidrome, enable first-artist-only scrobbling:

```toml
ND_LASTFM_SCROBBLEFIRSTARTISTONLY = true
```

Navidrome reads the individual artists from `ARTISTS` and submits only the
first one. Other players that support multi-value artist tags work the same
way.

If your scrobbler only reads the singular `ARTIST` tag, set **ARTIST tag** to
**A - primary artist only**.

> Multi-value tags require a format that supports them. For MP3, prefer
> ID3v2.4. ID3v2.3 can only flatten multiple values into one string.

## Primary artist and Spotify order

The plugin does not call the Spotify API and needs no account or API key.

1. By default, the first MusicBrainz track artist is the primary artist.
2. If the file already contains a Spotify-style order, the first name is
   kept when that same name appears in the MusicBrainz credit.
3. That order is applied when the file is linked to a track and again before
   the file is saved.

For an album credited to both artists, every album artist is preserved:

```text
ALBUMARTIST  = A; B        (multi-value)
ALBUMARTISTS = A; B        (multi-value)
```

To deliberately file a collaboration album under one artist, set
**ALBUMARTIST/ALBUMARTISTS** to **First artist only**.

## Compatibility

- MusicBrainz Picard 3.x (plugin API 3.0)
- Tested with Picard 3.0.2
- Python 3.9 or newer

## Development

The artist-splitting rules live in `core.py` and have no Picard or Qt
dependencies, so the unit tests run with plain Python:

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).
