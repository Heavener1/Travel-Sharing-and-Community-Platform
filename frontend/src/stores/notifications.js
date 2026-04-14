import { defineStore } from "pinia";

import http from "../api/http";

export const useNotificationStore = defineStore("notifications", {
  state: () => ({
    items: [],
    unreadCount: 0,
    open: false,
    loading: false,
    pollTimer: null,
  }),
  actions: {
    async fetchNotifications() {
      this.loading = true;
      try {
        const { data } = await http.get("/social/notifications/", { meta: { silentLoading: true, silentError: true } });
        this.items = data.results || [];
        this.unreadCount = data.unread_count || 0;
      } finally {
        this.loading = false;
      }
    },
    async markAllRead() {
      await http.post("/social/notifications/read/", null, { meta: { silentLoading: true, silentError: true } });
      this.unreadCount = 0;
      this.items = this.items.map((item) => ({ ...item, is_read: true }));
    },
    async togglePanel() {
      this.open = !this.open;
      if (this.open) {
        await this.fetchNotifications();
        if (this.unreadCount > 0) {
          await this.markAllRead();
        }
      }
    },
    startPolling() {
      this.stopPolling();
      this.pollTimer = window.setInterval(() => {
        this.fetchNotifications().catch(() => {});
      }, 30000);
    },
    stopPolling() {
      if (this.pollTimer) {
        window.clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    },
    reset() {
      this.items = [];
      this.unreadCount = 0;
      this.open = false;
      this.loading = false;
      this.stopPolling();
    },
  },
});
