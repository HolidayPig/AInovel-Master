<template>
  <Transition name="capsule">
    <div v-if="visible" class="capsule-wrap">
      <div class="capsule">
        <div v-if="props.phase !== 'done' && props.phase !== 'error'" class="capsule-bar" />
        <span class="capsule-text">{{ statusText }}</span>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    visible: boolean;
    phase?: "prepare" | "thinking" | "writing" | "done" | "error";
  }>(),
  { phase: "prepare" }
);

const statusText = computed(() => {
  const map: Record<string, string> = {
    prepare: "✨ 准备上下文...",
    thinking: "🤔 AI 思考中...",
    writing: "✍️ 正在生成小说...",
    done: "✓ 完成",
    error: "✕ 出错了",
  };
  return map[props.phase] ?? "处理中...";
});
</script>

<style scoped>
.capsule-wrap {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}
.capsule {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.8);
}
.capsule-bar {
  width: 48px;
  height: 4px;
  border-radius: 2px;
  background: linear-gradient(
    90deg,
    var(--el-color-primary) 0%,
    var(--el-color-primary-light-3) 50%,
    var(--el-color-primary) 100%
  );
  background-size: 200% 100%;
  animation: capsule-progress 1.2s ease-in-out infinite;
}
.capsule-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.capsule-enter-active,
.capsule-leave-active {
  transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.2, 0, 0, 1);
}
.capsule-enter-from,
.capsule-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-8px);
}
.capsule-enter-to,
.capsule-leave-from {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
@keyframes capsule-progress {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
</style>
