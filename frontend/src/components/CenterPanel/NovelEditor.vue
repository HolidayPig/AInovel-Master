<template>
  <div class="novel-editor">
    <editor-content v-if="editor" :editor="editor" class="editor-content" />
    <div v-else class="editor-loading">加载中...</div>
  </div>
</template>

<script setup lang="ts">
import { watch, onBeforeUnmount } from "vue";
import { useEditor, EditorContent } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";

const props = defineProps<{
  modelValue: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const editor = useEditor({
  content: props.modelValue || "<p></p>",
  extensions: [StarterKit],
  editorProps: {
    attributes: {
      class: "prose prose-sm max-w-none focus:outline-none min-h-[300px]",
    },
  },
  onUpdate: ({ editor }) => {
    emit("update:modelValue", editor.getHTML());
  },
});

watch(
  () => props.modelValue,
  (val) => {
    if (editor.value && val !== editor.value.getHTML()) {
      editor.value.commands.setContent(val || "<p></p>", false);
    }
  }
);

onBeforeUnmount(() => {
  editor.value?.destroy();
});
</script>

<style scoped>
.novel-editor {
  height: 100%;
}
.editor-content {
  height: 100%;
}
.editor-content :deep(.ProseMirror) {
  min-height: 300px;
  padding: 12px;
  line-height: 1.8;
}
.editor-loading {
  padding: 24px;
  color: var(--el-text-color-secondary);
}
</style>
