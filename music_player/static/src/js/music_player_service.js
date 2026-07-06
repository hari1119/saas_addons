/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

const musicPlayerService = {
    dependencies: ["notification", "orm"],

    start(env, { notification, orm }) {
        const audio = new Audio();
        audio.preload = "metadata";

        const state = reactive({
            track: false,
            selectedId: false,
            queue: [],
            onlineTracks: [],
            onlineMode: false,
            onlineEndpoint: "",
            onlineError: "",
            repeatMode: "off",
            shuffle: false,
            isPlaying: false,
            isAnimating: false,
            isBuffering: false,
            currentTime: 0,
            duration: 0,
        });

        async function loadConfig() {
            try {
                const config = await orm.call("music.track", "get_player_config", []);
                state.onlineMode = Boolean(config.online_mode);
                state.onlineEndpoint = config.online_endpoint || "";
                if (!state.onlineEndpoint) {
                    state.onlineMode = false;
                }
            } catch {
                state.onlineMode = false;
                state.onlineEndpoint = "";
            }
        }

        loadConfig();

        function getPlaybackUrl(track) {
            return track.audio_url || "";
        }

        function resolveRemoteUrl(url, endpoint) {
            if (!url) {
                return "";
            }
            return new URL(url, endpoint).href;
        }

        async function loadOnlineTracks() {
            state.onlineError = "";
            if (!state.onlineEndpoint) {
                state.onlineTracks = [];
                state.onlineError = "Online track list endpoint is not configured.";
                notification.add(state.onlineError, { type: "warning" });
                return [];
            }
            try {
                const response = await fetch(state.onlineEndpoint);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const payload = await response.json();
                const tracks = Array.isArray(payload) ? payload : payload.tracks || [];
                state.onlineTracks = tracks.map((track, index) => ({
                    id: track.id || `online-${index}`,
                    source: "online",
                    name: track.name || track.title || "Online Track",
                    artist: track.artist || "",
                    album: track.album || "",
                    genre: track.genre || "",
                    audio_url: resolveRemoteUrl(track.audio_url, state.onlineEndpoint),
                    cover_url: resolveRemoteUrl(track.cover_url || track.image_url, state.onlineEndpoint),
                    duration_display: track.duration_display || "",
                    duration_seconds: track.duration_seconds || 0,
                    favorite: false,
                    play_count: track.play_count || 0,
                    playlist_ids: track.playlist_ids || [],
                })).filter((track) => track.audio_url);
                return state.onlineTracks;
            } catch (error) {
                state.onlineTracks = [];
                state.onlineError = `Could not load online tracks: ${error.message}`;
                notification.add(state.onlineError, { type: "danger" });
                return [];
            }
        }

        function setQueue(queue) {
            state.queue = Array.isArray(queue) ? queue : [];
        }

        function setTrack(track) {
            if (!track) {
                return;
            }
            state.track = track;
            state.selectedId = track.id;
            const audioUrl = getPlaybackUrl(track);
            if (audioUrl && audio.src !== new URL(audioUrl, window.location.origin).href) {
                audio.src = audioUrl;
                state.currentTime = 0;
                state.duration = 0;
            }
        }

        async function markPlayed(track) {
            if (track.source === "online") {
                return;
            }
            try {
                await orm.call("music.track", "action_mark_played", [[track.id]]);
                track.play_count = (track.play_count || 0) + 1;
            } catch {
                // Playback should continue even if the play-count RPC fails.
            }
        }

        async function playTrack(track, queue = false, markAsPlayed = true) {
            if (queue) {
                setQueue(queue);
            }
            if (!track || !getPlaybackUrl(track)) {
                if (state.onlineMode) {
                    notification.add("Online endpoint is not configured for this track.", {
                        type: "warning",
                    });
                }
                return;
            }
            setTrack(track);
            state.isPlaying = true;
            state.isBuffering = true;
            state.isAnimating = false;
            try {
                await audio.play();
                state.isPlaying = true;
                state.isBuffering = false;
                if (markAsPlayed) {
                    markPlayed(track);
                }
            } catch {
                state.isPlaying = false;
                state.isBuffering = false;
                state.isAnimating = false;
                notification.add("Your browser blocked playback. Press play again.", {
                    type: "warning",
                });
            }
        }

        function pause() {
            state.isPlaying = false;
            state.isBuffering = false;
            state.isAnimating = false;
            audio.pause();
        }

        function toggle() {
            if (!state.track) {
                return;
            }
            if (state.isPlaying) {
                pause();
            } else {
                playTrack(state.track, false, false);
            }
        }

        function setOnlineMode(value) {
            state.onlineMode = Boolean(value);
            if (state.onlineMode && !state.onlineEndpoint) {
                state.onlineMode = false;
                notification.add("Set the Online Track List Endpoint in Music Player Settings.", {
                    type: "warning",
                });
            }
        }

        function move(direction) {
            const queue = state.queue.length ? state.queue : state.track ? [state.track] : [];
            if (!queue.length) {
                return;
            }
            if (direction > 0 && state.repeatMode === "one" && state.track) {
                playTrack(state.track, false, false);
                return;
            }
            const currentIndex = Math.max(
                queue.findIndex((track) => track.id === state.selectedId),
                0
            );
            let nextIndex;
            if (direction > 0 && state.shuffle && queue.length > 1) {
                do {
                    nextIndex = Math.floor(Math.random() * queue.length);
                } while (nextIndex === currentIndex);
            } else {
                nextIndex = currentIndex + direction;
            }
            if (nextIndex < 0 || nextIndex >= queue.length) {
                if (state.repeatMode !== "all") {
                    pause();
                    return;
                }
                nextIndex = (nextIndex + queue.length) % queue.length;
            }
            playTrack(queue[nextIndex], queue);
        }

        function toggleRepeat() {
            const nextMode = {
                off: "all",
                all: "one",
                one: "off",
            };
            state.repeatMode = nextMode[state.repeatMode] || "off";
        }

        function toggleShuffle() {
            state.shuffle = !state.shuffle;
        }

        audio.addEventListener("timeupdate", () => {
            state.currentTime = audio.currentTime || 0;
            state.duration = audio.duration || 0;
        });
        audio.addEventListener("waiting", () => {
            if (state.isPlaying) {
                state.isBuffering = true;
                state.isAnimating = false;
            }
        });
        audio.addEventListener("canplay", () => {
            state.isBuffering = false;
            state.isAnimating = state.isPlaying && !audio.paused;
        });
        audio.addEventListener("playing", () => {
            state.isPlaying = true;
            state.isBuffering = false;
            state.isAnimating = true;
        });
        audio.addEventListener("loadedmetadata", () => {
            state.currentTime = 0;
            state.duration = audio.duration || 0;
        });
        audio.addEventListener("ended", () => {
            state.isPlaying = false;
            state.isBuffering = false;
            state.isAnimating = false;
            move(1);
        });
        audio.addEventListener("pause", () => {
            state.isPlaying = false;
            state.isBuffering = false;
            state.isAnimating = false;
        });
        audio.addEventListener("play", () => {
            state.isPlaying = true;
        });

        return {
            state,
            setQueue,
            setTrack,
            loadConfig,
            loadOnlineTracks,
            getPlaybackUrl,
            setOnlineMode,
            toggleRepeat,
            toggleShuffle,
            playTrack,
            pause,
            toggle,
            next: () => move(1),
            previous: () => move(-1),
        };
    },
};

registry.category("services").add("music_player", musicPlayerService);
