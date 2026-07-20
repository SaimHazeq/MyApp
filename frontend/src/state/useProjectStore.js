import { create } from "zustand";
import { projectService } from "../services/projectService";

export const useProjectStore = create((set, get) => ({
  projects: [],
  projectsLoading: false,
  current: null,
  currentLoading: false,

  async fetchProjects() {
    set({ projectsLoading: true });
    try {
      const projects = await projectService.list();
      set({ projects, projectsLoading: false });
    } catch (err) {
      set({ projectsLoading: false });
      throw err;
    }
  },

  async fetchProject(projectId) {
    set({ currentLoading: true });
    try {
      const project = await projectService.get(projectId);
      set({ current: project, currentLoading: false });
      return project;
    } catch (err) {
      set({ currentLoading: false });
      throw err;
    }
  },

  async createProject(payload) {
    const project = await projectService.create(payload);
    set({ projects: [project, ...get().projects] });
    return project;
  },

  async removeProject(projectId) {
    await projectService.remove(projectId);
    set({ projects: get().projects.filter((p) => p.id !== projectId) });
  },

  patchLocalProject(projectId, patch) {
    set({
      projects: get().projects.map((p) => (p.id === projectId ? { ...p, ...patch } : p)),
      current: get().current?.id === projectId ? { ...get().current, ...patch } : get().current,
    });
  },
}));
