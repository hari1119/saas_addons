# -*- coding: utf-8 -*-

import base64
import ipaddress
import re
import socket
import struct
from cgi import parse_header
from pathlib import PurePosixPath
from urllib.parse import parse_qs, quote, quote_plus, unquote, urlencode, urlparse

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


MAX_AUDIO_IMPORT_BYTES = 50 * 1024 * 1024
YOUTUBE_API_KEY_PARAM = "music_player.youtube_api_key"
ONLINE_MODE_PARAM = "music_player.online_mode"
ONLINE_ENDPOINT_PARAM = "music_player.online_endpoint"
SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac")
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class MusicTrack(models.Model):
    _name = "music.track"
    _description = "Music Track"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "favorite desc, name"

    name = fields.Char(required=True, tracking=True, default="New Track")
    artist = fields.Char(index=True, tracking=True)
    album = fields.Char(index=True)
    genre = fields.Char(index=True)
    source_url = fields.Char(string="Source URL")
    thumbnail_url = fields.Char(readonly=True)
    link_status = fields.Char(readonly=True)
    metadata_source = fields.Char(readonly=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    favorite = fields.Boolean(default=False)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    audio_file = fields.Binary(
        string="Audio File",
        attachment=True,
    )
    audio_filename = fields.Char(string="Audio Filename")
    audio_url = fields.Char(compute="_compute_audio_url")
    online_audio_url = fields.Char(compute="_compute_online_audio_url")
    cover_image = fields.Image(
        string="Cover",
        max_width=1024,
        max_height=1024,
    )

    playlist_ids = fields.Many2many(
        "music.playlist",
        "music_playlist_track_rel",
        "track_id",
        "playlist_id",
        string="Playlists",
    )
    duration_seconds = fields.Integer(string="Duration")
    duration_display = fields.Char(
        string="Duration",
        compute="_compute_duration_display",
    )
    play_count = fields.Integer(readonly=True, default=0)
    last_played = fields.Datetime(readonly=True)

    def _can_replace_name(self):
        self.ensure_one()
        return not self.name or self.name == "New Track"

    @api.depends("audio_file", "audio_filename")
    def _compute_audio_url(self):
        for track in self:
            if track.id and track.audio_file:
                filename = quote(track.audio_filename or f"{track.name}.mp3")
                track.audio_url = (
                    f"/web/content/music.track/{track.id}/audio_file/{filename}?download=false"
                )
            else:
                track.audio_url = False

    @api.depends("audio_filename", "name")
    def _compute_online_audio_url(self):
        endpoint = self.env["ir.config_parameter"].sudo().get_param(ONLINE_ENDPOINT_PARAM, "").strip()
        for track in self:
            track.online_audio_url = track._build_online_audio_url(endpoint)

    def _build_online_audio_url(self, endpoint):
        self.ensure_one()
        if not endpoint:
            return False

        filename = self.audio_filename or f"{self.name}.mp3"
        replacements = {
            "{id}": str(self.id or ""),
            "{name}": quote(self.name or "", safe=""),
            "{filename}": quote(filename, safe=""),
            "{audio_filename}": quote(filename, safe=""),
        }
        url = endpoint
        for token, value in replacements.items():
            url = url.replace(token, value)
        if url != endpoint:
            return url

        separator = "&" if "?" in endpoint else "?"
        return "%s%s%s" % (
            endpoint,
            separator,
            urlencode({
                "track_id": self.id,
                "filename": filename,
            }),
        )

    @api.depends("duration_seconds")
    def _compute_duration_display(self):
        for track in self:
            if not track.duration_seconds:
                track.duration_display = False
                continue
            minutes, seconds = divmod(track.duration_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                track.duration_display = f"{hours:d}:{minutes:02d}:{seconds:02d}"
            else:
                track.duration_display = f"{minutes:d}:{seconds:02d}"

    @staticmethod
    def _decode_synchsafe(value):
        return (
            ((value[0] & 0x7F) << 21)
            | ((value[1] & 0x7F) << 14)
            | ((value[2] & 0x7F) << 7)
            | (value[3] & 0x7F)
        )

    @staticmethod
    def _decode_id3_text(value):
        if not value:
            return False
        encoding = value[0]
        raw = value[1:]
        try:
            if encoding == 0:
                return raw.decode("latin1").strip("\x00").strip()
            if encoding == 1:
                return raw.decode("utf-16").strip("\x00").strip()
            if encoding == 2:
                return raw.decode("utf-16-be").strip("\x00").strip()
            if encoding == 3:
                return raw.decode("utf-8").strip("\x00").strip()
        except UnicodeDecodeError:
            return False
        return False

    @staticmethod
    def _id3_text_separator(encoding):
        return b"\x00\x00" if encoding in (1, 2) else b"\x00"

    def _extract_id3_cover(self, frame_data):
        if not frame_data:
            return False
        encoding = frame_data[0]
        payload = frame_data[1:]
        mime_end = payload.find(b"\x00")
        if mime_end < 0:
            return False
        payload = payload[mime_end + 1:]
        if not payload:
            return False
        payload = payload[1:]
        separator = self._id3_text_separator(encoding)
        description_end = payload.find(separator)
        if description_end < 0:
            return False
        image_data = payload[description_end + len(separator):]
        return base64.b64encode(image_data).decode() if image_data else False

    def _read_audio_metadata(self, audio_file):
        if not audio_file:
            return {}
        try:
            data = base64.b64decode(audio_file)
        except Exception:
            return {}
        if len(data) < 10 or data[:3] != b"ID3":
            return {}

        version = data[3]
        tag_size = self._decode_synchsafe(data[6:10])
        cursor = 10
        tag_end = min(len(data), cursor + tag_size)
        metadata = {}
        text_frames = {
            "TIT2": "name",
            "TPE1": "artist",
            "TALB": "album",
            "TCON": "genre",
        }
        while cursor + 10 <= tag_end:
            frame_id = data[cursor:cursor + 4].decode("latin1", errors="ignore")
            if not frame_id.strip("\x00"):
                break
            size_data = data[cursor + 4:cursor + 8]
            frame_size = (
                self._decode_synchsafe(size_data)
                if version == 4
                else struct.unpack(">I", size_data)[0]
            )
            cursor += 10
            if frame_size <= 0 or cursor + frame_size > tag_end:
                break
            frame_data = data[cursor:cursor + frame_size]
            if frame_id in text_frames:
                value = self._decode_id3_text(frame_data)
                if value:
                    metadata[text_frames[frame_id]] = value
            elif frame_id == "APIC":
                cover_image = self._extract_id3_cover(frame_data)
                if cover_image:
                    metadata["cover_image"] = cover_image
            cursor += frame_size
        return metadata

    @api.onchange("audio_file", "audio_filename")
    def _onchange_audio_file_metadata(self):
        for track in self:
            metadata = track._read_audio_metadata(track.audio_file)
            if not metadata:
                if track.audio_filename and track._can_replace_name():
                    track.name = PurePosixPath(track.audio_filename).stem.replace("_", " ").replace("-", " ")
                continue
            if metadata.get("name") and track._can_replace_name():
                track.name = metadata["name"]
            for field_name in ("artist", "album", "genre", "cover_image"):
                if metadata.get(field_name) and not track[field_name]:
                    track[field_name] = metadata[field_name]
            track.link_status = _("Audio metadata fetched from the uploaded file.")

    def _ensure_source_url(self):
        self.ensure_one()
        if not self.source_url:
            raise UserError(_("Please paste a source URL first."))
        return self._validate_external_url(self.source_url.strip())

    def _validate_external_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise UserError(_("Please enter a valid http or https URL."))
        hostname = parsed.hostname.lower()
        if hostname in ("localhost",) or hostname.endswith(".local"):
            raise UserError(_("Local/private network URLs are not allowed."))
        try:
            address_infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as error:
            raise UserError(_("Could not resolve the URL host: %s") % error) from error
        for address_info in address_infos:
            ip_address = ipaddress.ip_address(address_info[4][0])
            if (
                ip_address.is_private
                or ip_address.is_loopback
                or ip_address.is_link_local
                or ip_address.is_multicast
                or ip_address.is_reserved
            ):
                raise UserError(_("Local/private network URLs are not allowed."))
        return url

    def _is_youtube_url(self, url):
        host = (urlparse(url).hostname or "").lower()
        return host in YOUTUBE_HOSTS or host.endswith(".youtube.com")

    def _extract_youtube_video_id(self, url):
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path_parts = [part for part in parsed.path.split("/") if part]
        if host in ("youtu.be", "www.youtu.be") and path_parts:
            return path_parts[0]
        query_video_id = parse_qs(parsed.query).get("v")
        if query_video_id:
            return query_video_id[0]
        for marker in ("shorts", "embed", "live"):
            if marker in path_parts:
                marker_index = path_parts.index(marker)
                if len(path_parts) > marker_index + 1:
                    return path_parts[marker_index + 1]
        return False

    def _parse_youtube_duration(self, value):
        if not value:
            return 0
        match = re.fullmatch(
            r"P(?:(?P<days>\d+)D)?"
            r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
            value,
        )
        if not match:
            return 0
        parts = {key: int(number or 0) for key, number in match.groupdict().items()}
        return (
            parts["days"] * 86400
            + parts["hours"] * 3600
            + parts["minutes"] * 60
            + parts["seconds"]
        )

    def _safe_get(self, url, **kwargs):
        try:
            return requests.get(
                url,
                timeout=kwargs.pop("timeout", 15),
                headers={
                    "User-Agent": "Odoo Music Player/1.0",
                    **kwargs.pop("headers", {}),
                },
                **kwargs,
            )
        except requests.RequestException as error:
            raise UserError(_("Could not fetch the URL: %s") % error) from error

    def _filename_from_response(self, response, url):
        content_type = response.headers.get("Content-Type", "").split(";")[0]
        extension_by_type = {
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/ogg": ".ogg",
            "audio/mp4": ".m4a",
            "audio/aac": ".aac",
            "audio/flac": ".flac",
        }
        fallback_extension = extension_by_type.get(content_type, ".mp3")
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition:
            _, params = parse_header(content_disposition)
            if params.get("filename"):
                filename = params["filename"]
                if not filename.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS):
                    filename = "%s%s" % (filename, fallback_extension)
                return filename
        path_name = PurePosixPath(unquote(urlparse(url).path)).name
        if path_name:
            if not path_name.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS):
                path_name = "%s%s" % (path_name, fallback_extension)
            return path_name
        return "imported_audio%s" % fallback_extension

    def _metadata_endpoint(self, url):
        if self._is_youtube_url(url):
            return "https://www.youtube.com/oembed?url=%s&format=json" % quote_plus(url)
        return "https://noembed.com/embed?url=%s" % quote_plus(url)

    def _fetch_youtube_data_api_metadata(self, url):
        video_id = self._extract_youtube_video_id(url)
        if not video_id:
            return {}
        api_key = self.env["ir.config_parameter"].sudo().get_param(YOUTUBE_API_KEY_PARAM)
        if not api_key:
            return {}
        response = self._safe_get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,contentDetails",
                "id": video_id,
                "key": api_key,
            },
        )
        if response.status_code >= 400:
            raise UserError(_("YouTube Data API returned an error: %s") % response.text)
        try:
            payload = response.json()
        except ValueError as error:
            raise UserError(_("The YouTube Data API response was not valid JSON.")) from error
        items = payload.get("items") or []
        if not items:
            raise UserError(_("No YouTube video details were found for this link."))
        item = items[0]
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = (
            thumbnails.get("maxres")
            or thumbnails.get("standard")
            or thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )
        return {
            "title": snippet.get("title"),
            "artist": snippet.get("channelTitle"),
            "thumbnail_url": thumbnail.get("url"),
            "duration_seconds": self._parse_youtube_duration(content_details.get("duration")),
            "description": snippet.get("description"),
            "metadata_source": _("YouTube Data API"),
        }

    def action_fetch_link_details(self):
        for track in self:
            url = track._ensure_source_url()
            metadata = {}
            if track._is_youtube_url(url):
                metadata = track._fetch_youtube_data_api_metadata(url)
            if not metadata:
                response = track._safe_get(track._metadata_endpoint(url))
                if response.status_code >= 400:
                    raise UserError(_("No public metadata was found for this link."))
                try:
                    metadata = response.json()
                except ValueError as error:
                    raise UserError(_("The metadata response was not valid JSON.")) from error
                metadata["metadata_source"] = _("Public oEmbed metadata")

            values = {
                "thumbnail_url": metadata.get("thumbnail_url"),
                "metadata_source": metadata.get("metadata_source"),
                "link_status": _("Details fetched from the source link."),
            }
            if metadata.get("title") and track._can_replace_name():
                values["name"] = metadata["title"]
            if metadata.get("artist") and not track.artist:
                values["artist"] = metadata["artist"]
            if metadata.get("duration_seconds") and not track.duration_seconds:
                values["duration_seconds"] = metadata["duration_seconds"]
            if metadata.get("description") and not track.description:
                values["description"] = metadata["description"]

            thumbnail_url = metadata.get("thumbnail_url")
            if thumbnail_url and not track.cover_image:
                track._validate_external_url(thumbnail_url)
                image_response = track._safe_get(thumbnail_url, timeout=10)
                if image_response.status_code < 400 and image_response.content:
                    values["cover_image"] = base64.b64encode(image_response.content).decode()
            track.write(values)
        return True

    def action_fetch_direct_audio(self):
        for track in self:
            url = track._ensure_source_url()
            if track._is_youtube_url(url):
                raise UserError(_(
                    "YouTube audio cannot be downloaded here. Paste a direct audio file URL "
                    "from a source you own or are authorized to use."
                ))
            response = track._safe_get(url, stream=True)
            if response.status_code >= 400:
                raise UserError(_("The audio file URL returned an error: %s") % response.status_code)
            filename = track._filename_from_response(response, url)
            lower_filename = filename.lower()
            content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
            if not lower_filename.endswith(SUPPORTED_AUDIO_EXTENSIONS) and not content_type.startswith("audio/"):
                raise UserError(_("This URL does not look like a direct supported audio file."))

            chunks = []
            total_size = 0
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                total_size += len(chunk)
                if total_size > MAX_AUDIO_IMPORT_BYTES:
                    raise UserError(_("Audio imports are limited to 50 MB."))
                chunks.append(chunk)
            if not chunks:
                raise UserError(_("No audio data was received from the URL."))

            values = {
                "audio_file": base64.b64encode(b"".join(chunks)).decode(),
                "audio_filename": filename,
                "link_status": _("Direct audio file fetched and stored on this track."),
            }
            title = PurePosixPath(filename).stem.replace("_", " ").replace("-", " ").strip()
            if title and track._can_replace_name():
                values["name"] = title
            track.write(values)
            track._onchange_audio_file_metadata()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if not values.get("audio_file"):
                source_url = values.get("source_url")
                if not source_url:
                    raise UserError(_("Please upload an audio file or add a source URL before saving."))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("audio_file") is False:
            raise UserError(_("A music track must keep an audio file."))
        return super().write(vals)

    def action_mark_played(self):
        for track in self:
            track.write({
                "play_count": track.play_count + 1,
                "last_played": fields.Datetime.now(),
            })
        return True

    def action_toggle_favorite(self):
        for track in self:
            track.favorite = not track.favorite
        return True

    @api.model
    def get_player_config(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "online_mode": params.get_param(ONLINE_MODE_PARAM, "False") == "True",
            "online_endpoint": params.get_param(ONLINE_ENDPOINT_PARAM, ""),
        }
