# Contributing

Issues and pull requests are welcome.

## Development

The plugin targets MusicBrainz Picard 3.x and requires no third-party Python
packages for its unit tests.

```bash
git clone <repository-url> separate_artists
cd separate_artists
python3 -m unittest discover -s tests -v
```

Picard loads a plugin directory as a Python module, so use a checkout folder
named `separate_artists` when testing with **Options → Plugins → Local**.

## Pull requests

- Keep the artist-parsing logic in `core.py` independent of Picard and Qt.
- Add or update tests for behavior changes.
- Update `CHANGELOG.md` for user-visible changes.
- Keep the README focused on plugin usage.

## Releasing

1. Update `version` in `MANIFEST.toml`, `PLUGIN_VERSION` in `__init__.py`, and
   `CHANGELOG.md`.
2. Run the unit tests.
3. Commit the release changes and create a tag such as `v1.1.0`.
4. Push the commit and tag.
5. Create a GitHub release and attach the plugin archive built from the
   repository root.
