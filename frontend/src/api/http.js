import axios from "axios";

import { pinia } from "../stores";
import { useUiStore } from "../stores/ui";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api",
  timeout: 20000,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("travel_access_token");
  const uiStore = useUiStore(pinia);
  config.meta = config.meta || {};

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (!config.meta.silentLoading) {
    uiStore.startRequest();
  }
  return config;
});

http.interceptors.response.use(
  (response) => {
    const uiStore = useUiStore(pinia);
    if (!response.config.meta?.silentLoading) {
      uiStore.finishRequest();
    }
    return response;
  },
  async (error) => {
    const uiStore = useUiStore(pinia);
    const config = error.config || {};

    if (!config.meta?.silentLoading) {
      uiStore.finishRequest();
    }

    const shouldRetry =
      !config.__retried &&
      (config.method || "get").toLowerCase() === "get" &&
      (error.code === "ECONNABORTED" || !error.response || error.response.status >= 500);

    if (shouldRetry) {
      config.__retried = true;
      return http(config);
    }

    if (!config.meta?.silentError) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        (error.code === "ECONNABORTED" ? "请求超时，请稍后重试。" : "请求失败，请稍后再试。");
      uiStore.pushToast(message, "error");
    }

    return Promise.reject(error);
  },
);

export default http;
