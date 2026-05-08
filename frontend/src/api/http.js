import axios from "axios";

import { pinia } from "../stores";
import { useUiStore } from "../stores/ui";

// ── 请求缓存 (GET 去重 + 短时缓存) ──
const pendingRequests = new Map();
const responseCache = new Map();
const CACHE_TTL = 30000; // 30 秒

function getCacheKey(config) {
  return `${config.method || "get"}:${config.url}:${JSON.stringify(config.params || {})}`;
}

function getCachedResponse(cacheKey) {
  const entry = responseCache.get(cacheKey);
  if (entry && Date.now() - entry.ts < CACHE_TTL) {
    return entry.data;
  }
  responseCache.delete(cacheKey);
  return null;
}

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

  // GET 请求：缓存命中直接返回，未命中则去重
  const method = (config.method || "get").toLowerCase();
  if (method === "get" && !config.meta.skipCache) {
    const cacheKey = getCacheKey(config);
    const cached = getCachedResponse(cacheKey);
    if (cached) {
      config.__cachedResponse = cached;
      config.adapter = () =>
        Promise.resolve({ data: cached, status: 200, statusText: "OK", headers: {}, config });
      return config;
    }
    // 去重：相同请求正在飞行中，复用 Promise
    if (pendingRequests.has(cacheKey)) {
      config.adapter = () => pendingRequests.get(cacheKey);
      return config;
    }
    config.__cacheKey = cacheKey;
  }

  if (!config.meta.silentLoading) {
    uiStore.startRequest();
  }
  return config;
});

http.interceptors.response.use(
  (response) => {
    const uiStore = useUiStore(pinia);
    const config = response.config || {};

    if (!config.meta?.silentLoading) {
      uiStore.finishRequest();
    }

    // 缓存 GET 响应 + 清理 pending
    if (config.__cacheKey) {
      responseCache.set(config.__cacheKey, { data: response.data, ts: Date.now() });
      pendingRequests.delete(config.__cacheKey);
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

    // 失败时清理 pending，让下次请求重新发起
    if (config.__cacheKey) {
      pendingRequests.delete(config.__cacheKey);
    }

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
