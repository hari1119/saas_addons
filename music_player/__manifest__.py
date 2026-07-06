# -*- coding: utf-8 -*-
{
    "name": "Music Player",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Upload, organize, and play music tracks inside Odoo.",
    "description": """
Music Player
============
Manage an internal music library with tracks, playlists, and an inline browser audio player.
    """,
    "author": "Hari",
    "website": "https://www.yourcompany.com",
    "license": "LGPL-3",
    "images": ["static/description/icon.png"],
    "depends": [
        "base",
        "mail",
        "web",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/music_track_views.xml",
        "views/music_playlist_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "music_player/static/src/js/audio_player_field.js",
            "music_player/static/src/js/music_player_service.js",
            "music_player/static/src/js/music_studio.js",
            "music_player/static/src/js/music_systray.js",
            "music_player/static/src/xml/audio_player_field.xml",
            "music_player/static/src/xml/music_studio.xml",
            "music_player/static/src/xml/music_systray.xml",
            "music_player/static/src/scss/audio_player.scss",
            "music_player/static/src/scss/music_studio.scss",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
