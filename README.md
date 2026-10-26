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
each artist separately.

A single-artist album stays single (`ALBUMARTIST = A`,
`ALBUMARTISTS = A`). Multi-artist albums are never reduced to the first
artist.

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
- Works automatically with zero configuration while albums load.
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

## Zero configuration

There are no settings. Enable the plugin and it applies the recommended
layout automatically:

- while an album is loaded from MusicBrainz (album and track metadata),
- when a file is matched to a track,
- and once more just before a file is saved.

Load your albums, save, done. The right-click **Separate Artists
(Spotify-style)** action re-applies the rules to files that were tagged
before the plugin was installed.

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
