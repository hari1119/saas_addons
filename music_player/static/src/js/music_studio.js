/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillStart, useState } from "@odoo/owl";

class MusicStudio extends Component {
    static template = "music_player.MusicStudio";

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.player = useService("music_player");
        this.state = useState({
            loading: true,
            query: "",
            activePlaylistId: false,
            localTracks: [],
            localPlaylists: [],
            tracks: [],
            playlists: [],
        });

        onWillStart(async () => {
            await this.player.loadConfig();
            await this.loadLibrary();
        });
        onMounted(() => {
            if (!this.player.state.selectedId && this.state.tracks.length) {
                this.player.setTrack(this.state.tracks[0]);
            }
        });
    }

    async loadLibrary() {
        this.state.loading = true;
        try {
            const [tracks, playlists] = await Promise.all([
                this.orm.searchRead(
                    "music.track",
                    [],
                    [
                        "name",
                        "artist",
                        "album",
                        "genre",
                        "audio_filename",
                        "audio_url",
                        "online_audio_url",
                        "duration_display",
                        "play_count",
                        "favorite",
                        "playlist_ids",
                    ],
                    { limit: 500, order: "create_date desc, favorite desc, name" }
                ),
                this.orm.searchRead(
                    "music.playlist",
                    [],
                    ["name", "track_count", "track_ids"],
                    { limit: 50, order: "name" }
                ),
            ]);
            this.state.localTracks = tracks;
            this.state.localPlaylists = playlists;
            await this.applyPlaybackSource();
        } catch {
            this.notification.add("Could not load the music library.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async applyPlaybackSource() {
        if (this.player.state.onlineMode) {
            const onlineTracks = await this.player.loadOnlineTracks();
            this.state.tracks = onlineTracks;
            this.state.playlists = [];
            this.state.activePlaylistId = false;
        } else {
            this.state.tracks = this.state.localTracks;
            this.state.playlists = this.state.localPlaylists;
        }
        this.player.setQueue(this.filteredTracks);
        if (!this.player.state.isPlaying && this.filteredTracks.length) {
            this.player.setTrack(this.filteredTracks[0]);
        }
    }

    get selectedTrack() {
        return (
            this.player.state.track ||
            this.state.tracks.find((track) => track.id === this.player.state.selectedId) ||
            false
        );
    }

    get activePlaylist() {
        return this.state.playlists.find((playlist) => playlist.id === this.state.activePlaylistId);
    }

    get filteredTracks() {
        const query = this.state.query.trim().toLowerCase();
        return this.state.tracks.filter((track) => {
            const matchesPlaylist =
                !this.state.activePlaylistId ||
                (track.playlist_ids || []).includes(this.state.activePlaylistId);
            const haystack = [track.name, track.artist, track.album, track.genre]
                .filter(Boolean)
                .join(" ")
                .toLowerCase();
            return matchesPlaylist && (!query || haystack.includes(query));
        });
    }

    get totalPlays() {
        return this.state.tracks.reduce((total, track) => total + (track.play_count || 0), 0);
    }

    get favoriteCount() {
        return this.state.tracks.filter((track) => track.favorite).length;
    }

    get progressStyle() {
        const duration = this.player.state.duration || 0;
        const percent = duration
            ? Math.min((this.player.state.currentTime / duration) * 100, 100)
            : 0;
        return `width: ${percent}%`;
    }

    coverUrl(track) {
        if (track.cover_url) {
            return track.cover_url;
        }
        return `/web/image/music.track/${track.id}/cover_image`;
    }

    selectPlaylist(playlistId) {
        this.state.activePlaylistId = playlistId;
        this.player.setQueue(this.filteredTracks);
        const firstTrack = this.filteredTracks[0];
        if (
            firstTrack &&
            !this.player.state.isPlaying &&
            !this.filteredTracks.some((track) => track.id === this.player.state.selectedId)
        ) {
            this.player.setTrack(firstTrack);
        }
    }

    onSearch(ev) {
        this.state.query = ev.target.value;
        window.setTimeout(() => this.player.setQueue(this.filteredTracks));
    }

    async togglePlaybackMode() {
        this.player.setOnlineMode(!this.player.state.onlineMode);
        await this.applyPlaybackSource();
    }

    toggleRepeat() {
        this.player.toggleRepeat();
    }

    toggleShuffle() {
        this.player.toggleShuffle();
    }

    playTrack(track) {
        this.player.playTrack(track, this.filteredTracks);
    }

    togglePlay() {
        this.player.toggle();
    }

    nextTrack() {
        this.player.next();
    }

    previousTrack() {
        this.player.previous();
    }

    async toggleFavorite(track, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        if (track.source === "online") {
            this.notification.add("Online tracks cannot be favorited on this system.", {
                type: "info",
            });
            return;
        }
        await this.orm.call("music.track", "action_toggle_favorite", [[track.id]]);
        track.favorite = !track.favorite;
    }

    openTrack(track, ev) {
        ev.stopPropagation();
        if (track.source === "online") {
            this.notification.add("Open the source system to edit this online track.", {
                type: "info",
            });
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "music.track",
            res_id: track.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    createTrack() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "music.track",
            views: [[false, "form"]],
            target: "current",
        });
    }

    formatTime(value) {
        const totalSeconds = Math.max(0, Math.floor(value || 0));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = String(totalSeconds % 60).padStart(2, "0");
        return `${minutes}:${seconds}`;
    }
}

registry.category("actions").add("music_player.music_studio", MusicStudio);

export { MusicStudio };
