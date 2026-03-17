<template>
  <el-dialog
    v-model="visible"
    title="新建章节"
    width="520px"
    destroy-on-close
    append-to-body
    align-center
    @close="emit('close')"
  >
    <el-form :model="form" label-width="100px" label-position="left">
      <el-form-item label="章节名称">
        <el-input v-model="form.title" placeholder="第一章、第二章…" />
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
      <el-button type="primary" @click="submit">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

const props = defineProps<{
  modelValue: boolean;
  novelId: number;
  nextChapterIndex: number;
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  close: [];
  saved: [payload: { title: string; summary: string; target_words: number }];
}>();

const visible = ref(props.modelValue);
const form = ref({ title: "", summary: "", target_words: 0 });

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v;
    if (v) {
      const idx = props.nextChapterIndex;
      form.value = {
        title: `第${idx}章`,
        summary: "",
        target_words: 0,
      };
    }
  }
);
watch(visible, (v) => emit("update:modelValue", v));

function submit() {
  const title = form.value.title.trim() || `第${props.nextChapterIndex}章`;
  emit("saved", {
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
