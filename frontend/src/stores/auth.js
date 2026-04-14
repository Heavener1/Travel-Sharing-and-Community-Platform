import { defineStore } from "pinia";

import http from "../api/http";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    access: localStorage.getItem("travel_access_token") || "",
    refresh: localStorage.getItem("travel_refresh_token") || "",
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.access && state.user),
  },
  actions: {
    async login(payload) {
      const { data } = await http.post("/auth/login/", payload);
      this.access = data.access;
      this.refresh = data.refresh;
      localStorage.setItem("travel_access_token", data.access);
      localStorage.setItem("travel_refresh_token", data.refresh);
      await this.fetchMe();
    },
    async register(payload) {
      const { data } = await http.post("/auth/register/", payload);
      this.access = data.access;
      this.refresh = data.refresh;
      this.user = data.user;
      localStorage.setItem("travel_access_token", data.access);
      localStorage.setItem("travel_refresh_token", data.refresh);
    },
    async fetchMe() {
      if (!this.access) return;
      const { data } = await http.get("/auth/me/");
      this.user = data;
    },
    async updateMe(payload) {
      const { data } = await http.patch("/auth/me/", payload);
      this.user = data;
    },
    async restore() {
      if (this.access && !this.user) {
        try {
          await this.fetchMe();
        } catch {
          this.logout();
        }
      }
    },
    logout() {
      this.user = null;
      this.access = "";
      this.refresh = "";
      localStorage.removeItem("travel_access_token");
      localStorage.removeItem("travel_refresh_token");
    },
  },
});
