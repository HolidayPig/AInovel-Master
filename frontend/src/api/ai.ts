export interface GenerateParams {
  settings_id: number;
  novel_id: number;
  chapter_id: number | null;
  author_id: number | null;
  context: string;
  prompt: string;
  web_search_enabled?: boolean;
}

export type StreamEvent =
  | { type: "delta"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

export async function streamGenerate(
  params: GenerateParams,
  onEvent: (ev: StreamEvent) => void
): Promise<void> {
  const res = await fetch("/api/ai/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.text();
    onEvent({ type: "error", message: err || `HTTP ${res.status}` });
    return;
  }
  const reader = res.body?.getReader();
  if (!reader) {
    onEvent({ type: "error", message: "No response body" });
    return;
  }
  const dec = new TextDecoder();
  let buf = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();
          if (!data) continue;
          try {
            const ev = JSON.parse(data) as StreamEvent;
            onEvent(ev);
            if (ev.type === "error" || ev.type === "done") return;
          } catch {
            // skip malformed
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
  onEvent({ type: "done" });
}
