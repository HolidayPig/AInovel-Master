import axios from "axios";
import { ElMessage } from "element-plus";

export const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const raw = err.response?.data?.detail ?? err.response?.data?.message ?? err.message ?? "请求失败";
    const msg = Array.isArray(raw)
      ? raw.map((e: { msg?: string }) => e?.msg).filter(Boolean).join("；") || "请求失败"
      : typeof raw === "string"
        ? raw
        : String(raw);
    ElMessage.error(msg);
    return Promise.reject(err);
  }
);
