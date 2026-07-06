# -*- coding: utf-8 -*-

import secrets

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    music_player_online_mode = fields.Boolean(
        string="Online Playback Mode",
        config_parameter="music_player.online_mode",
    )
    music_player_online_endpoint = fields.Char(
        string="Online Track List Endpoint",
        config_parameter="music_player.online_endpoint",
        help=(
            "Remote JSON endpoint used when Music Studio is in online mode. "
            "Expected response: {'tracks': [{'name': ..., 'audio_url': ...}]}."
        ),
    )
    music_player_share_enabled = fields.Boolean(
        string="Expose Local Library",
        config_parameter="music_player.share_enabled",
    )
    music_player_share_token = fields.Char(
        string="Share Token",
        config_parameter="music_player.share_token",
    )
    music_player_share_url = fields.Char(
        string="This System Track List URL",
        compute="_compute_music_player_share_url",
    )

    @api.depends("music_player_share_token")
    def _compute_music_player_share_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for settings in self:
            if settings.music_player_share_token and base_url:
                settings.music_player_share_url = (
                    f"{base_url}/music_player/share/tracks?token={settings.music_player_share_token}"
                )
            else:
                settings.music_player_share_url = False

    @api.model
    def get_values(self):
        values = super().get_values()
        if not values.get("music_player_share_token"):
            values["music_player_share_token"] = secrets.token_urlsafe(24)
        return values

    def action_generate_music_player_share_token(self):
        self.ensure_one()
        token = secrets.token_urlsafe(24)
        self.env["ir.config_parameter"].sudo().set_param("music_player.share_token", token)
        self.music_player_share_token = token
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.config.settings",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }
