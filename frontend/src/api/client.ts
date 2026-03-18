import axios from "axios";
import { ElMessage } from "element-plus";

export const api = axios.create({
  baseURL: "/api",
  timeout: 120000,
  headers: { "Content-Type": "application/json" },
});

function formatApiError(err: unknown): string {
  if (!axios.isAxiosError(err)) {
    return err instanceof Error ? err.message || "请求失败" : "请求失败";
  }
  const code = err.code;
  if (code === "ECONNABORTED" || err.message?.includes("timeout")) {
    return "请求超时。生成章节耗时较长，请减小「预计总章数」后重试，或检查网络与后端是否正常运行。";
  }
  if (!err.response) {
    return err.message?.trim() || "网络异常，无法连接服务器（请确认后端已启动且地址正确）";
  }
  const status = err.response.status;
  const data = err.response.data;
  if (typeof data === "string" && data.trim()) {
    const t = data.replace(/<[^>]+>/g, " ").trim().slice(0, 200);
    return t || `服务器返回 ${status}`;
  }
  if (data && typeof data === "object") {
    const d = (data as { detail?: unknown; message?: unknown }).detail;
    const m = (data as { message?: unknown }).message;
    if (Array.isArray(d)) {
      const parts = d.map((e: { msg?: string; type?: string; loc?: unknown }) => {
        const msg = (e?.msg || "").trim();
        if (!msg) return "";
        const loc = Array.isArray(e?.loc) ? e.loc.join(".") : "";
        return loc ? `${loc}: ${msg}` : msg;
      });
      const joined = parts.filter(Boolean).join("；");
      if (joined) return joined;
    }
    if (typeof d === "string" && d.trim()) return d.trim();
    if (d && typeof d === "object") {
      try {
        const s = JSON.stringify(d);
        if (s && s !== "{}") return s.slice(0, 300);
      } catch {
        /* ignore */
      }
    }
    if (typeof m === "string" && m.trim()) return m.trim();
  }
  if (status === 504) {
    return (
      (data as { detail?: string })?.detail ||
      "网关或模型响应超时，请减小「预计总章数」或检查反向代理读超时是否过短（建议 ≥600 秒）。"
    );
  }
  if (status >= 500) {
    return `服务器错误 (${status})，请查看后端日志。生成章节若失败常见原因：API Key、模型不可用或模型输出非合法 JSON。`;
  }
  return err.message?.trim() || `请求失败 (HTTP ${status})`;
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = formatApiError(err).trim() || "请求失败，未返回具体说明";
    ElMessage.error({ message: msg, duration: 0, showClose: true });
    return Promise.reject(err);
  }
);
