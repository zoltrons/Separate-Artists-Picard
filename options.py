"""Picard v3 options page for Separate Artists."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from picard.plugin3.api import OptionsPage

try:  # plugin package import (normal Picard loading)
    from .config import get_option
except ImportError:  # top-level import used by tooling/tests
    from config import get_option


class SeparateArtistsOptionsPage(OptionsPage):
    NAME = 'separate_artists'
    TITLE = 'Separate Artists'
    PARENT = 'plugins'

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        intro = QLabel(
            'Splits multi-artist credits such as "A & B" into one value per '
            'artist in ARTIST/ARTISTS and ALBUMARTIST/ALBUMARTISTS. '
            'Multi-artist albums keep all of their album artists.'
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        behaviour = QGroupBox('Artist tags')
        form = QFormLayout(behaviour)

        self.multi_value_artists = QCheckBox(
            'Write ARTIST/ALBUMARTIST as multiple values (recommended)'
        )
        self.multi_value_artists.setToolTip(
            'Players such as Navidrome then link every artist separately. '
            'Off joins the artists into one string with the display separator.'
        )
        form.addRow('', self.multi_value_artists)

        self.artist_separator = QLineEdit()
        self.artist_separator.setPlaceholderText(', ')
        self.artist_separator.setMaximumWidth(120)
        form.addRow('Display separator:', self.artist_separator)

        self.artist_tag_mode = QComboBox()
        self.artist_tag_mode.addItem('A; B - every artist', 'all')
        self.artist_tag_mode.addItem('A - primary artist only', 'primary')
        form.addRow('ARTIST tag:', self.artist_tag_mode)

        self.album_artist_mode = QComboBox()
        self.album_artist_mode.addItem(
            'Preserve all album artists (recommended)', 'all'
        )
        self.album_artist_mode.addItem(
            'First artist only (Spotify-style)', 'first'
        )
        self.album_artist_mode.addItem('Leave unchanged', 'keep')
        form.addRow('ALBUMARTIST/ALBUMARTISTS:', self.album_artist_mode)

        self.collapse_albumartists = QCheckBox(
            'Collapse ALBUMARTISTS to the primary artist'
        )
        self.collapse_albumartists.setToolTip(
            'Only used by the first-artist mode. Off keeps every album artist.'
        )
        form.addRow('', self.collapse_albumartists)

        layout.addWidget(behaviour)

        source = QGroupBox('Source and fallback')
        source_form = QFormLayout(source)

        self.prefer_original_primary = QCheckBox(
            "Use the file's existing first artist when it also appears in the "
            'MusicBrainz credit'
        )
        self.prefer_original_primary.setToolTip(
            'Useful for files tagged by a Spotify downloader: the Spotify '
            'artist order is preserved instead of being replaced by the '
            'MusicBrainz order.'
        )
        source_form.addRow('', self.prefer_original_primary)

        self.split_existing = QCheckBox(
            'Split plain artist strings when no multi-value MusicBrainz credit '
            'is available'
        )
        source_form.addRow('', self.split_existing)

        layout.addWidget(source)

        advanced = QGroupBox('Advanced')
        advanced_form = QFormLayout(advanced)

        self.extra_separators = QPlainTextEdit()
        self.extra_separators.setPlaceholderText('One separator per line, e.g.  x ')
        self.extra_separators.setMaximumHeight(80)
        advanced_form.addRow('Extra separators:', self.extra_separators)

        self.never_split = QPlainTextEdit()
        self.never_split.setPlaceholderText('One artist name per line')
        self.never_split.setMinimumHeight(120)
        advanced_form.addRow('Never split:', self.never_split)

        note = QLabel(
            'The never-split list is only needed when the plugin has to parse '
            'a plain string. MusicBrainz multi-value credits are always '
            'trusted.'
        )
        note.setWordWrap(True)
        advanced_form.addRow('', note)

        layout.addWidget(advanced)
        layout.addStretch()

        self.album_artist_mode.currentIndexChanged.connect(
            self._update_album_artist_controls
        )
        self.multi_value_artists.toggled.connect(
            self._update_separator_controls
        )
        self._update_separator_controls()
        self._update_album_artist_controls()

    def _update_album_artist_controls(self, *_args):
        self.collapse_albumartists.setEnabled(
            self.album_artist_mode.currentData() == 'first'
        )

    def _update_separator_controls(self, *_args):
        self.artist_separator.setEnabled(
            not self.multi_value_artists.isChecked()
        )

    def load(self):
        config = self.api.plugin_config
        self.multi_value_artists.setChecked(
            bool(get_option(config, 'multi_value_artists'))
        )
        self.artist_separator.setText(
            get_option(config, 'artist_separator')
        )
        self.artist_tag_mode.setCurrentIndex(
            max(
                0,
                self.artist_tag_mode.findData(
                    get_option(config, 'artist_tag_mode')
                ),
            )
        )
        self.album_artist_mode.setCurrentIndex(
            max(
                0,
                self.album_artist_mode.findData(
                    get_option(config, 'album_artist_mode')
                ),
            )
        )
        self.collapse_albumartists.setChecked(
            bool(
                get_option(config, 'collapse_albumartists')
            )
        )
        self.prefer_original_primary.setChecked(
            bool(
                get_option(config, 'prefer_original_primary')
            )
        )
        self.split_existing.setChecked(
            bool(
                get_option(config, 'split_existing')
            )
        )
        self.extra_separators.setPlainText(
            str(get_option(config, 'extra_separators'))
        )
        self.never_split.setPlainText(
            str(get_option(config, 'never_split'))
        )
        self._update_album_artist_controls()
        self._update_separator_controls()

    def save(self):
        config = self.api.plugin_config
        separator = self.artist_separator.text()
        if not separator.strip():
            separator = ', '
        config['artist_separator'] = separator
        config['multi_value_artists'] = self.multi_value_artists.isChecked()
        config['artist_tag_mode'] = self.artist_tag_mode.currentData()
        config['album_artist_mode'] = self.album_artist_mode.currentData()
        config['collapse_albumartists'] = self.collapse_albumartists.isChecked()
        config['prefer_original_primary'] = self.prefer_original_primary.isChecked()
        config['split_existing'] = self.split_existing.isChecked()
        config['extra_separators'] = self.extra_separators.toPlainText()
        config['never_split'] = self.never_split.toPlainText()
