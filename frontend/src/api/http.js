import axios from "axios";

import { pinia } from "../stores";
import { useUiStore } from "../stores/ui";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api",
  timeout: 20000,
});

const isStandardEnvelope = (payload) =>
  payload &&
  typeof payload === "object" &&
  Object.prototype.hasOwnProperty.call(payload, "status_code") &&
  Object.prototype.hasOwnProperty.call(payload, "data") &&
  Object.prototype.hasOwnProperty.call(payload, "message");

const unwrapEnvelope = (response) => {
  if (isStandardEnvelope(response.data)) {
    response.api = {
      statusCode: response.data.status_code,
      message: response.data.message,
    };
    response.data = response.data.data;
  }
  return response;
};

const getErrorMessage = (error) => {
  const payload = error?.response?.data;
  if (error?.response?.api?.message) {
    return error.response.api.message;
  }
  if (isStandardEnvelope(payload)) {
    return payload.message || payload.data?.detail || "请求失败，请稍后再试。";
  }
  return (
    payload?.detail ||
    payload?.message ||
    (error.code === "ECONNABORTED" ? "请求超时，请稍后重试。" : "请求失败，请稍后再试。")
  );
};

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
    return unwrapEnvelope(response);
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

    if (isStandardEnvelope(error?.response?.data)) {
      const envelope = error.response.data;
      error.response.api = {
        statusCode: envelope.status_code,
        message: envelope.message,
      };
      error.response.data = envelope.data;
    }

    if (!config.meta?.silentError) {
      uiStore.pushToast(getErrorMessage(error), "error");
    }

    return Promise.reject(error);
  },
);

export default http;
