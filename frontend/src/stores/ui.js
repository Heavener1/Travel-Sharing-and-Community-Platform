import { defineStore } from "pinia";

let toastSeed = 1;

export const useUiStore = defineStore("ui", {
  state: () => ({
    routeLoading: false,
    pendingRequests: 0,
    toasts: [],
  }),
  getters: {
    showGlobalLoading: (state) => state.routeLoading || state.pendingRequests > 0,
  },
  actions: {
    setRouteLoading(value) {
      this.routeLoading = value;
    },
    startRequest() {
      this.pendingRequests += 1;
    },
    finishRequest() {
      this.pendingRequests = Math.max(0, this.pendingRequests - 1);
    },
    pushToast(message, type = "error") {
      const id = toastSeed++;
      this.toasts.push({ id, message, type });
      window.setTimeout(() => {
        this.toasts = this.toasts.filter((item) => item.id !== id);
      }, 3200);
    },
  },
});
