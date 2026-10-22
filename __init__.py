"""Separate Artists - a MusicBrainz Picard 3 plugin.

The plugin turns Picard's joined artist credit ("A & B") into Navidrome /
Spotify-style tags:

    ARTIST       = A, B
    ARTISTS      = A; B       (multi-value)
    ALBUMARTIST  = A, B       (all album artists)
    ALBUMARTISTS = A; B       (multi-value)

The first artist is treated as the primary artist.  Multi-artist albums keep
all of their album artists; only the optional first-artist mode collapses
them.  When the file already contains a Spotify-style artist order, that
order is preferred as long as the name also exists in the MusicBrainz credit.
"""

from __future__ import annotations

from .config import load_config, register_options
from .core import apply_split


PLUGIN_NAME = 'Separate Artists'
PLUGIN_VERSION = '1.1.0'


def _original_for_track(track):
    files = getattr(track, 'files', None) or ()
    for file in files:
        original = getattr(file, 'orig_metadata', None)
        if original is not None:
            return original
    return None


def _iter_targets(obj, album_cls, track_cls, file_cls, cluster_cls):
    """Yield ``(metadata, original_metadata)`` pairs for a Picard object."""

    if isinstance(obj, album_cls):
        for track in getattr(obj, 'tracks', ()) or ():
            yield track.metadata, _original_for_track(track)
            for file in getattr(track, 'files', ()) or ():
                yield file.metadata, getattr(file, 'orig_metadata', None)
        return
    if isinstance(obj, track_cls):
        yield obj.metadata, _original_for_track(obj)
        for file in getattr(obj, 'files', ()) or ():
            yield file.metadata, getattr(file, 'orig_metadata', None)
        return
    if isinstance(obj, file_cls):
        yield obj.metadata, getattr(obj, 'orig_metadata', None)
        return
    if isinstance(obj, cluster_cls):
        for file in getattr(obj, 'files', ()) or ():
            yield file.metadata, getattr(file, 'orig_metadata', None)
        return
    metadata = getattr(obj, 'metadata', None)
    if metadata is not None:
        yield metadata, None


def _describe(result) -> str:
    if not result.changed:
        return 'no changes'
    parts = [', '.join(result.artists)]
    if result.album_primary:
        parts.append(f'album artist: {result.album_primary}')
    return '; '.join(parts)


def process_track(api, track, metadata, track_node, release_node=None):
    """Automatically split artists when MusicBrainz metadata is loaded."""

    from picard.plugin3.api import DebugOpt

    result = apply_split(metadata, load_config(api))
    if result.changed:
        api.logger.debug_if(
            DebugOpt.PLUGIN_DEVELOPMENT,
            'Separate Artists: %s -> %s',
            metadata.get('title', track),
            _describe(result),
        )
    return result


def _apply_to_file(api, file, stage, mark_changed=False):
    from picard.plugin3.api import DebugOpt

    result = apply_split(
        file.metadata,
        load_config(api),
        original_metadata=getattr(file, 'orig_metadata', None),
    )
    if result.changed:
        api.logger.debug_if(
            DebugOpt.PLUGIN_DEVELOPMENT,
            'Separate Artists: %s %s -> %s',
            stage,
            getattr(file, 'filename', file),
            _describe(result),
        )
        if mark_changed:
            update = getattr(file, 'update', None)
            if callable(update):
                update(update_selection=False)
    return result


def process_file_added(api, track, file):
    """Apply the file's Spotify order as soon as it is linked to a track."""

    return _apply_to_file(api, file, 'file-added', mark_changed=True)


def process_pre_save(api, file):
    """Re-apply the rules at save time, using the file's original order."""

    return _apply_to_file(api, file, 'pre-save')


def enable(api):
    """Picard v3 entry point."""

    from picard.plugin3.api import (
        Album,
        BaseAction,
        Cluster,
        File,
        Track,
    )

    from .options import SeparateArtistsOptionsPage

    api.logger.info('%s %s loaded', PLUGIN_NAME, PLUGIN_VERSION)

    register_options(api)

    class SeparateArtistsAction(BaseAction):
        TITLE = 'Separate Artists (Spotify-style)'

        def callback(self, objs):
            config = load_config(self.api)
            changed = 0
            dirty = []
            dirty_ids = set()
            for obj in objs:
                for metadata, original in _iter_targets(
                    obj, Album, Track, File, Cluster
                ):
                    result = apply_split(
                        metadata, config, original_metadata=original
                    )
                    if result.changed:
                        changed += 1
                        if id(obj) not in dirty_ids:
                            dirty_ids.add(id(obj))
                            dirty.append(obj)
            for obj in dirty:
                update = getattr(obj, 'update', None)
                if callable(update):
                    update()
            if changed:
                self.api.logger.info(
                    'Separate Artists: updated %d metadata object(s)', changed
                )
            else:
                self.api.logger.info('Separate Artists: nothing to change')

    # Run after most other metadata plugins so we see their final artist
    # values, and late during save so we win over older tag values.
    api.register_track_metadata_processor(process_track, priority=-50)
    api.register_file_post_addition_to_track_processor(
        process_file_added, priority=-50
    )
    api.register_file_pre_save_processor(process_pre_save, priority=-50)

    api.register_options_page(SeparateArtistsOptionsPage)
    api.register_track_action(SeparateArtistsAction)
    api.register_file_action(SeparateArtistsAction)
    api.register_album_action(SeparateArtistsAction)
    api.register_cluster_action(SeparateArtistsAction)


def disable():
    """Registrations are removed automatically by Picard."""
