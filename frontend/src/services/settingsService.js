import { api } from "./api";

export const settingsService = {
  async get() {
    const { data } = await api.get("/settings/me");
    return data;
  },
  async updateProfile(payload) {
    const { data } = await api.patch("/settings/profile", payload);
    return data;
  },
  async updatePreferences(payload) {
    const { data } = await api.patch("/settings/preferences", payload);
    return data;
  },
  async changePassword(payload) {
    await api.post("/settings/change-password", payload);
  },
  async deleteAccount() {
    await api.delete("/settings/account");
  },
};
