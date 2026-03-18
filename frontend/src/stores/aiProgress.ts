import { defineStore } from "pinia";
import { ref } from "vue";

export type AiPhase =
  | "prepare"
  | "thinking"
  | "writing"
  | "querying"
  | "processing"
  | "done"
  | "error";

const COLORS = [
  { from: "#409eff", to: "#79bbff" },
  { from: "#67c23a", to: "#95d475" },
  { from: "#e6a23c", to: "#f0c78a" },
  { from: "#9c27b0", to: "#ce93d8" },
  { from: "#00bcd4", to: "#80deea" },
  { from: "#ff9800", to: "#ffb74d" },
];

export const useAiProgressStore = defineStore("aiProgress", () => {
  const visible = ref(false);
  const phase = ref<AiPhase>("prepare");
  const operation = ref("");
  const detail = ref("");
  const elapsedSeconds = ref(0);
  const barColor = ref({ ...COLORS[0]! });
  let hideTimer: ReturnType<typeof setTimeout> | null = null;
  let tickTimer: ReturnType<typeof setInterval> | null = null;
  let startedAt = 0;
  let lastUserDetailAt = 0;

  function clearHide() {
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
  }

  function clearTick() {
    if (tickTimer) {
      clearInterval(tickTimer);
      tickTimer = null;
    }
  }

  function startTick() {
    clearTick();
    startedAt = Date.now();
    elapsedSeconds.value = 0;
    tickTimer = setInterval(() => {
      if (!visible.value) return;
      const now = Date.now();
      elapsedSeconds.value = Math.floor((now - startedAt) / 1000);
      // 如果长时间没有新 detail，自动补一句“仍在工作”避免用户误判卡死
      if (
        !["done", "error"].includes(phase.value) &&
        now - lastUserDetailAt > 8000
      ) {
        // 不覆盖写作预览
        if (!detail.value.startsWith("正在输出：")) {
          detail.value = (detail.value || "任务进行中…").trim();
        }
      }
    }, 1000);
  }

  function start(op: string, opts?: { phase?: AiPhase; detail?: string }) {
    clearHide();
    clearTick();
    operation.value = op;
    phase.value = opts?.phase ?? "prepare";
    detail.value = opts?.detail ?? "";
    lastUserDetailAt = Date.now();
    barColor.value = COLORS[Math.floor(Math.random() * COLORS.length)]!;
    visible.value = true;
    startTick();
  }

  function setPhase(p: AiPhase, d?: string) {
    phase.value = p;
    if (d !== undefined) {
      detail.value = d;
      lastUserDetailAt = Date.now();
    }
  }

  function setDetail(d: string, maxLen = 240) {
    const s = d.replace(/\s+/g, " ").trim();
    detail.value = s.length > maxLen ? s.slice(0, maxLen) + "…" : s;
    lastUserDetailAt = Date.now();
  }

  /** 流式续写：展示末尾片段 */
  function appendWritingPreview(streamTail: string) {
    const t = streamTail.replace(/\s+/g, " ").trimEnd().slice(-120);
    detail.value = t ? `正在输出：${t}` : "正在生成正文，请稍候…";
    lastUserDetailAt = Date.now();
  }

  function finishSuccess(ms = 500) {
    clearHide();
    clearTick();
    phase.value = "done";
    hideTimer = setTimeout(() => {
      visible.value = false;
      hideTimer = null;
    }, ms);
  }

  function finishError(ms = 1800) {
    clearHide();
    clearTick();
    phase.value = "error";
    hideTimer = setTimeout(() => {
      visible.value = false;
      hideTimer = null;
    }, ms);
  }

  return {
    visible,
    phase,
    operation,
    detail,
    elapsedSeconds,
    barColor,
    start,
    setPhase,
    setDetail,
    appendWritingPreview,
    finishSuccess,
    finishError,
    clearHide,
  };
});
