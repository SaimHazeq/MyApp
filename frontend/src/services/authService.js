import { api, tokenStorage } from "./api";

export const authService = {
  async register({ fullName, email, password }) {
    const { data } = await api.post("/auth/register", {
      full_name: fullName,
      email,
      password,
    });
    tokenStorage.set(data.access_token, data.refresh_token);
    return data.user;
  },

  async login({ email, password }) {
    const { data } = await api.post("/auth/login", { email, password });
    tokenStorage.set(data.access_token, data.refresh_token);
    return data.user;
  },

  async me() {
    const { data } = await api.get("/auth/me");
    return data;
  },

  logout() {
    tokenStorage.clear();
  },

  isAuthenticated() {
    return Boolean(tokenStorage.getAccess());
  },
};
