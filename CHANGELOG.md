# Changelog

All notable changes to this project are documented in this file.

## 1.3.0 - 2026-10-26

### Changed

- Zero configuration: the options page and all plugin settings are removed.
  The recommended layout (one value per artist, every album artist kept,
  Spotify order preserved) is always used.
- Split album artists automatically while an album is loaded, in addition to
  the existing track, file-match and pre-save hooks.

## 1.2.0 - 2026-10-26

### Changed

- Write `ARTIST` and `ALBUMARTIST` (and their sort tags) as multi-value tags
  with one value per artist, the way Picard writes `ARTISTS`. A joined string
  such as `The Weeknd;Lana Del Rey` was shown by Navidrome as one artist.
- The display separator is now only used when the new "multiple values"
  option is turned off.

## 1.1.1 - 2026-10-26

### Fixed

- Read settings with item access. Picard 3's `ConfigSection` has no `.get()`,
  so every metadata hook, the right-click action and the options page failed
  with `AttributeError`.
- Read the global "Various Artists" name the same way instead of silently
  falling back to the default.

## 1.1.0 - 2026-10-22

### Changed

- Preserve all album artists on multi-artist albums by default.
- Keep `ALBUMARTIST`, `ALBUMARTISTS`, and the MusicBrainz album artist IDs
  multi-valued.
- Preserve all artist sort names in the default all-artists mode.
- Migrate the old 1.0.0 collapse default once for existing installations.

## 1.0.0 - 2026-10-21

### Added

- Initial release.
- Split joined artist credits into `ARTIST`/`ARTISTS` tags.
- Write album artist tags with a selectable first-artist or all-artists mode.
- Preserve Spotify-style artist order from existing file tags.
- Add a right-click action and an options page.
