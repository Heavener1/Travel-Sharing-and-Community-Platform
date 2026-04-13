const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

const parseEventBlocks = (buffer, onEvent) => {
  let cursor = buffer.indexOf("\n\n");
  while (cursor !== -1) {
    const rawBlock = buffer.slice(0, cursor);
    buffer = buffer.slice(cursor + 2);
    const lines = rawBlock.split("\n");
    let event = "message";
    const dataLines = [];
    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (dataLines.length) {
      try {
        onEvent(event, JSON.parse(dataLines.join("\n")));
      } catch {
        onEvent(event, { raw: dataLines.join("\n") });
      }
    }
    cursor = buffer.indexOf("\n\n");
  }
  return buffer;
};

export const streamRequest = async ({ path, method = "POST", body, onEvent }) => {
  const token = localStorage.getItem("travel_access_token");
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let detail = "流式请求失败。";
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = parseEventBlocks(buffer, onEvent);
  }
  if (buffer.trim()) {
    parseEventBlocks(`${buffer}\n\n`, onEvent);
  }
};
