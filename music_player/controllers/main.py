# -*- coding: utf-8 -*-

import base64
import json
import mimetypes

from odoo import http
from odoo.http import request


class MusicPlayerShareController(http.Controller):
    def _share_config(self):
        params = request.env["ir.config_parameter"].sudo()
        return {
            "enabled": params.get_param("music_player.share_enabled", "False") == "True",
            "token": params.get_param("music_player.share_token", ""),
        }

    def _check_token(self, token):
        config = self._share_config()
        return config["enabled"] and config["token"] and token == config["token"]

    def _forbidden(self):
        return request.make_response(
            json.dumps({"error": "Forbidden"}),
            headers=[
                ("Content-Type", "application/json"),
                ("Access-Control-Allow-Origin", "*"),
            ],
            status=403,
        )

    def _base_url(self):
        return request.httprequest.host_url.rstrip("/")

    @http.route("/music_player/share/tracks", type="http", auth="public", csrf=False, cors="*")
    def shared_tracks(self, token=None, **kwargs):
        if not self._check_token(token):
            return self._forbidden()

        base_url = self._base_url()
        tracks = request.env["music.track"].sudo().search([("active", "=", True)], order="name")
        data = []
        for track in tracks:
            data.append({
                "id": track.id,
                "name": track.name,
                "artist": track.artist,
                "album": track.album,
                "genre": track.genre,
                "duration_seconds": track.duration_seconds,
                "duration_display": track.duration_display,
                "audio_url": f"{base_url}/music_player/share/audio/{track.id}?token={token}",
                "cover_url": f"{base_url}/music_player/share/cover/{track.id}?token={token}",
                "source_url": track.source_url,
            })

        return request.make_response(
            json.dumps({"tracks": data}),
            headers=[
                ("Content-Type", "application/json"),
                ("Access-Control-Allow-Origin", "*"),
            ],
        )

    @http.route("/music_player/share/audio/<int:track_id>", type="http", auth="public", csrf=False, cors="*")
    def shared_audio(self, track_id, token=None, **kwargs):
        if not self._check_token(token):
            return self._forbidden()

        track = request.env["music.track"].sudo().browse(track_id).exists()
        if not track or not track.audio_file:
            return request.not_found()

        filename = track.audio_filename or f"{track.name}.mp3"
        content = base64.b64decode(track.audio_file)
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return request.make_response(
            content,
            headers=[
                ("Content-Type", content_type),
                ("Content-Disposition", f'inline; filename="{filename}"'),
                ("Access-Control-Allow-Origin", "*"),
            ],
        )

    @http.route("/music_player/share/cover/<int:track_id>", type="http", auth="public", csrf=False, cors="*")
    def shared_cover(self, track_id, token=None, **kwargs):
        if not self._check_token(token):
            return self._forbidden()

        track = request.env["music.track"].sudo().browse(track_id).exists()
        if not track or not track.cover_image:
            return request.not_found()

        return request.make_response(
            base64.b64decode(track.cover_image),
            headers=[
                ("Content-Type", "image/png"),
                ("Access-Control-Allow-Origin", "*"),
            ],
        )
