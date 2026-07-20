import { api } from "./api";

export const projectService = {
  async list() {
    const { data } = await api.get("/projects");
    return data;
  },

  async get(projectId) {
    const { data } = await api.get(`/projects/${projectId}`);
    return data;
  },

  async create(payload) {
    const { data } = await api.post("/projects", payload);
    return data;
  },

  async update(projectId, payload) {
    const { data } = await api.patch(`/projects/${projectId}`, payload);
    return data;
  },

  async remove(projectId) {
    await api.delete(`/projects/${projectId}`);
  },

  async uploadCharacterReference(projectId, characterId, file) {
    const form = new FormData();
    form.append("file", file);
    const { data } = await api.post(
      `/storage/${projectId}/characters/${characterId}/reference-image`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },

  videoPath(projectId) {
    return `/storage/${projectId}/video`;
  },
  thumbnailPath(projectId) {
    return `/storage/${projectId}/thumbnail`;
  },
  subtitlesPath(projectId) {
    return `/storage/${projectId}/subtitles`;
  },
};
