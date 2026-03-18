<template>
  <Teleport to="body">
    <div class="ai-progress-anchor" aria-live="polite">
      <Transition name="ai-bar">
        <div v-if="store.visible" class="ai-progress-shell">
          <div class="ai-progress-top">
            <span class="ai-progress-op">{{ store.operation || "AI 任务" }}</span>
            <span class="ai-progress-badge" :class="'ph-' + store.phase">{{ phaseTitle }}</span>
          </div>
          <p class="ai-progress-detail">{{ displayDetail }}{{ elapsedSuffix }}</p>
          <div class="ai-progress-track-border">
            <div class="ai-progress-track">
              <div
                class="ai-progress-fill"
                :class="{ indeterminate: isWorking }"
                :style="fillStyle"
              />
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useAiProgressStore, type AiPhase } from "@/stores/aiProgress";

const store = useAiProgressStore();
const { phase, detail, barColor, elapsedSeconds } = storeToRefs(store);

const PHASE_TITLE: Record<AiPhase, string> = {
  prepare: "准备",
  thinking: "思考中",
  writing: "生成中",
  querying: "联网检索",
  processing: "处理中",
  done: "已完成",
  error: "异常",
};

const PHASE_HINT: Record<AiPhase, string> = {
  prepare: "正在组装上下文与请求参数…",
  thinking: "模型正在推理，尚未开始输出正文…",
  writing: "内容流式输出中，下方可预览最新片段…",
  querying: "正在访问网络并整理检索结果…",
  processing: "后台调用模型处理中，请勿关闭页面…",
  done: "本段任务已结束。",
  error: "请查看上方提示或重试。",
};

const phaseTitle = computed(() => PHASE_TITLE[phase.value] ?? "处理中");

const displayDetail = computed(() => {
  const d = (detail.value || "").trim();
  if (d) return d;
  return PHASE_HINT[phase.value] ?? "…";
});

const elapsedSuffix = computed(() => {
  if (!isWorking.value) return "";
  const s = elapsedSeconds.value ?? 0;
  if (s <= 0) return "";
  return ` · 已等待${s}s`;
});

const isWorking = computed(
  () => !["done", "error"].includes(phase.value)
);

const fillStyle = computed(() => ({
  background: `linear-gradient(90deg, ${barColor.value.from}, ${barColor.value.to})`,
}));
</script>

<style scoped>
.ai-progress-anchor {
  position: fixed;
  top: 64px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  z-index: 2147483646;
  pointer-events: none;
  padding: 0 12px;
  isolation: isolate;
}
.ai-progress-shell {
  pointer-events: auto;
  width: min(100%, 760px);
  padding: 14px 18px 16px;
  border-radius: 16px;
  border: 2px solid var(--el-color-primary);
  /* 不透明底，避免被侧栏/弹窗毛玻璃叠在下面导致看不清 */
  background: #ffffff;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.12),
    0 0 0 1px rgba(0, 0, 0, 0.06);
}
.ai-progress-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.ai-progress-op {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.ai-progress-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  flex-shrink: 0;
}
.ph-prepare,
.ph-thinking {
  background: var(--el-color-info-light-9);
  color: var(--el-color-info);
}
.ph-writing {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
.ph-querying {
  background: #e8f4fc;
  color: #0288d1;
}
.ph-processing {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}
.ph-done {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}
.ph-error {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}
.ai-progress-detail {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
  min-height: 2.4em;
  max-height: 4.6em;
  overflow-y: auto;
  word-break: break-word;
}
.ai-progress-track-border {
  padding: 3px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.04), rgba(255, 255, 255, 0.5));
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.06);
}
.ai-progress-track {
  height: 10px;
  border-radius: 7px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.06);
}
.ai-progress-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.35s cubic-bezier(0.32, 0.72, 0, 1);
}
.ai-progress-fill.indeterminate {
  width: 42%;
  animation: ai-progress-slide 1.5s ease-in-out infinite;
}
.ai-progress-fill:not(.indeterminate) {
  width: 100%;
}
@keyframes ai-progress-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(240%);
  }
}
.ai-bar-enter-active,
.ai-bar-leave-active {
  transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}
.ai-bar-enter-from,
.ai-bar-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
.ai-bar-enter-to,
.ai-bar-leave-from {
  opacity: 1;
  transform: translateY(0);
}
</style>
