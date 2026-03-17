<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑小说家' : '新建小说家'"
    width="520px"
    destroy-on-close
    append-to-body
    align-center
    @close="emit('close')"
  >
    <el-form :model="form" label-width="90px" label-position="left">
      <el-form-item label="名称">
        <el-input v-model="form.name" placeholder="如：东方玄幻小说家、言情小说家" />
      </el-form-item>
      <el-form-item label="编写风格">
        <el-input
          v-model="form.style"
          type="textarea"
          :rows="4"
          placeholder="描述该小说家的文风、用词习惯、叙事节奏等"
        />
      </el-form-item>
      <el-form-item label="排版方式">
        <el-input
          v-model="form.format_rules"
          type="textarea"
          :rows="3"
          placeholder="段落、标点、对话格式等排版要求"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import type { Author } from "@/types";

const props = defineProps<{
  modelValue: boolean;
  author: Author | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  close: [];
  saved: [payload: { id?: number; name: string; style: string; format_rules: string }];
}>();

const visible = ref(props.modelValue);
watch(
  () => props.modelValue,
  (v) => { visible.value = v; if (v) loadForm(); }
);
watch(visible, (v) => emit("update:modelValue", v));

const form = ref({ name: "", style: "", format_rules: "" });
const isEdit = ref(!!props.author);

function loadForm() {
  if (props.author) {
    form.value = {
      name: props.author.name,
      style: props.author.style ?? "",
      format_rules: props.author.format_rules ?? "",
    };
    isEdit.value = true;
  } else {
    form.value = { name: "", style: "", format_rules: "" };
    isEdit.value = false;
  }
}

function submit() {
  const name = form.value.name.trim();
  if (!name) return;
  emit("saved", {
    id: props.author?.id,
    name,
    style: form.value.style,
    format_rules: form.value.format_rules,
  });
  visible.value = false;
  emit("close");
}
</script>
