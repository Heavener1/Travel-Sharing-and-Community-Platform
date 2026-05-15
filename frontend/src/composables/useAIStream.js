/**
 * AI 流式响应 Composable — 封装 SSE 请求的 loading/progress/status/text 状态。
 * 通过 start() 发起流式请求，自动解析 progress/content/done/error 事件。
 */
import { ref } from "vue";
import { streamRequest } from "../api/stream";

export function useAIStream() {
  const loading = ref(false);
  const progress = ref(0);
  const status = ref("");
  const text = ref("");

  const start = async ({ path, body, method = "POST", initialStatus = "处理中...", doneMessage = "完成", errorFallback = "请求失败", onExtraEvent }) => {
    loading.value = true;
    progress.value = 0;
    status.value = initialStatus;
    text.value = "";

    try {
      await streamRequest({
        path,
        method,
        body,
        onEvent: (event, data) => {
          if (event === "progress") {
            progress.value = data.progress || 0;
            status.value = data.message || "";
          } else if (event === "content") {
            text.value = data.content || "";
          } else if (event === "done") {
            text.value = data.content || text.value;
            progress.value = 100;
            status.value = doneMessage;
          } else if (event === "error") {
            status.value = data.detail || errorFallback;
          } else if (onExtraEvent) {
            onExtraEvent(event, data);
          }
        },
      });
      return text.value;
    } catch (error) {
      status.value = error.message || errorFallback;
      return "";
    } finally {
      loading.value = false;
    }
  };

  return { loading, progress, status, text, start };
}
