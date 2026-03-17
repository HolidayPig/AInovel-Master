<template>
  <el-dialog
    v-model="visible"
    title="新建小说"
    width="520px"
    destroy-on-close
    append-to-body
    align-center
    @close="emit('close')"
  >
    <el-form :model="form" label-width="80px" label-position="left">
      <el-form-item label="小说名称">
        <el-input v-model="form.title" placeholder="输入小说名称" />
      </el-form-item>
      <el-form-item label="小说简介">
        <el-input v-model="form.description" type="textarea" :rows="3" placeholder="简要介绍小说内容" />
      </el-form-item>
      <el-form-item label="世界观">
        <el-input
          v-model="form.worldview"
          type="textarea"
          :rows="4"
          placeholder="可选。填写后将自动在右侧生成世界观卡片"
        />
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
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  close: [];
  saved: [payload: { title: string; description: string; worldview: string }];
}>();

const visible = ref(props.modelValue);
watch(
  () => props.modelValue,
  (v) => {
    visible.value = v;
    if (v) form.value = { title: "", description: "", worldview: "" };
  }
);
watch(visible, (v) => emit("update:modelValue", v));

const form = ref({ title: "", description: "", worldview: "" });

function submit() {
  const title = form.value.title.trim() || "未命名小说";
  emit("saved", {
    title,
    description: form.value.description.trim() || "",
    worldview: form.value.worldview.trim(),
  });
  visible.value = false;
  emit("close");
}
</script>
