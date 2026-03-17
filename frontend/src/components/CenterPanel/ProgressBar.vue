<template>
  <Transition name="bar">
    <div v-if="visible" class="progress-bar-wrap">
      <div class="progress-bar-track">
        <div
          class="progress-bar-fill"
          :class="{ indeterminate: phase !== 'done' && phase !== 'error' }"
          :style="fillStyle"
        />
      </div>
      <div class="progress-bar-label">{{ statusText }}</div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    visible: boolean;
    phase?: "prepare" | "thinking" | "writing" | "done" | "error";
    barColor?: { from: string; to: string };
  }>(),
  { phase: "prepare", barColor: () => ({ from: "#409eff", to: "#79bbff" }) }
);

const statusText = computed(() => {
  const map: Record<string, string> = {
    prepare: "准备上下文…",
    thinking: "AI 思考中…",
    writing: "正在生成小说…",
    done: "完成",
    error: "出错了",
  };
  return map[props.phase] ?? "处理中…";
});

const fillStyle = computed(() => ({
  background: `linear-gradient(90deg, ${props.barColor?.from ?? "#409eff"}, ${props.barColor?.to ?? "#79bbff"})`,
}));
</script>

<style scoped>
.progress-bar-wrap {
  position: fixed;
  top: 62px;
  left: 50%;
  transform: translateX(-50%);
  width: min(90%, 640px);
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.progress-bar-track {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.35s cubic-bezier(0.32, 0.72, 0, 1);
}
.progress-bar-fill.indeterminate {
  width: 45%;
  animation: progress-slide 1.6s ease-in-out infinite;
}
.progress-bar-fill:not(.indeterminate) {
  width: 100%;
}
.progress-bar-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
}
@keyframes progress-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(220%);
  }
}
.bar-enter-active,
.bar-leave-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}
.bar-enter-from,
.bar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-6px);
}
.bar-enter-to,
.bar-leave-from {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
</style>
