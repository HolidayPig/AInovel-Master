<template>
  <el-dialog
    v-model="visible"
    title="编辑章节"
    width="520px"
    destroy-on-close
    append-to-body
    align-center
    @close="emit('close')"
  >
    <el-form v-if="chapter" :model="form" label-width="100px" label-position="left">
      <el-form-item label="章节名称">
        <el-input v-model="form.title" placeholder="章节标题" />
      </el-form-item>
      <el-form-item label="内容梗概">
        <el-input
          v-model="form.summary"
          type="textarea"
          :rows="4"
          placeholder="本章节内容梗概，用于 AI 续写时参考"
        />
      </el-form-item>
      <el-form-item label="目标字数">
        <el-input-number v-model="form.target_words" :min="0" :max="50000" placeholder="可选" />
        <span class="hint">字（可选，0 表示不限制）</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { Chapter } from "@/types";

const props = defineProps<{
  modelValue: boolean;
  chapter: Chapter | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  close: [];
  saved: [payload: { id: number; title: string; summary: string; target_words: number }];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const form = ref({ title: "", summary: "", target_words: 0 });

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return;
    if (!props.chapter) return;
    form.value = {
      title: props.chapter.title || "",
      summary: props.chapter.summary || "",
      target_words: props.chapter.target_words || 0,
    };
  }
);

function submit() {
  if (!props.chapter) return;
  const title = form.value.title.trim() || props.chapter.title || "未命名章节";
  emit("saved", {
    id: props.chapter.id,
    title,
    summary: form.value.summary.trim(),
    target_words: form.value.target_words || 0,
  });
  visible.value = false;
  emit("close");
}
</script>

<style scoped>
.hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>

