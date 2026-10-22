# Changelog

All notable changes to this project are documented in this file.

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
