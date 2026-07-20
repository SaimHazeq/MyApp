import { api } from "./api";

export const generationService = {
  async start(projectId) {
    const { data } = await api.post(`/generation/${projectId}/start`);
    return data;
  },

  async status(projectId) {
    const { data } = await api.get(`/generation/${projectId}/status`);
    return data;
  },

  async cancel(projectId) {
    const { data } = await api.post(`/generation/${projectId}/cancel`);
    return data;
  },

  /** Polls status every `intervalMs` until a terminal state, invoking onUpdate each tick. */
  pollUntilDone(projectId, onUpdate, intervalMs = 1500) {
    let stopped = false;
    const tick = async () => {
      if (stopped) return;
      try {
        const data = await generationService.status(projectId);
        onUpdate(data);
        if (data.status !== "completed" && data.status !== "failed") {
          setTimeout(tick, intervalMs);
        }
      } catch (err) {
        onUpdate(null, err);
      }
    };
    tick();
    return () => {
      stopped = true;
    };
  },

  async exportPresets() {
    const { data } = await api.get("/render/presets");
    return data;
  },

  async exportMovie(projectId, preset, burnInSubtitles) {
    const { data } = await api.post(`/render/${projectId}/export`, {
      preset,
      burn_in_subtitles: burnInSubtitles,
    });
    return data;
  },
};
