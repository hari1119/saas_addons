# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MusicPlaylist(models.Model):
    _name = "music.playlist"
    _description = "Music Playlist"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
    track_ids = fields.Many2many(
        "music.track",
        "music_playlist_track_rel",
        "playlist_id",
        "track_id",
        string="Tracks",
    )
    track_count = fields.Integer(compute="_compute_track_count")

    @api.depends("track_ids")
    def _compute_track_count(self):
        for playlist in self:
            playlist.track_count = len(playlist.track_ids)

    def action_open_tracks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "music.track",
            "view_mode": "kanban,list,form",
            "domain": [("id", "in", self.track_ids.ids)],
            "context": {
                "default_playlist_ids": [(6, 0, [self.id])],
                "default_company_id": self.company_id.id,
            },
        }
