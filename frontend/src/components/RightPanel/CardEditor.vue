<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑卡片' : '新建卡片'"
    width="520px"
    destroy-on-close
    append-to-body
    align-center
    @close="emit('close')"
  >
    <el-form :model="form" label-width="80px" label-position="left">
      <el-form-item label="类型">
        <el-select
          v-model="form.card_type"
          placeholder="类型"
          style="width: 100%"
          :disabled="isEdit"
        >
          <el-option
            v-for="(label, key) in CARD_TYPE_LABELS"
            :key="key"
            :label="label"
            :value="key"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="名称">
        <el-input v-model="form.name" placeholder="卡片名称" />
      </el-form-item>
      <template v-for="f in currentFields" :key="f.key">
        <el-form-item :label="f.label">
          <el-input
            v-model="formFields[f.key]"
            type="textarea"
            :rows="6"
            :placeholder="placeholderText"
          />
        </el-form-item>
      </template>
      <el-form-item label="自动更新">
        <el-switch v-model="form.auto_update" />
        <span class="hint">开启后 AI 续写时会根据内容自动更新此卡片</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { CARD_TYPE_LABELS, CARD_TYPE_FIELDS, defaultContentJson } from "@/constants/cards";
import type { Card, CardType } from "@/types";

const props = defineProps<{
  modelValue: boolean;
  novelId: number;
  card: Card | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  close: [];
  saved: [
    payload: {
      id?: number;
      novel_id: number;
      card_type: string;
      name: string;
      content_json: string;
      auto_update: boolean;
    }
  ];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const isEdit = computed(() => !!props.card);

const form = ref({
  card_type: "character" as CardType,
  name: "",
  auto_update: false,
});

const formFields = ref<Record<string, string>>({});

const currentFields = computed(
  () => CARD_TYPE_FIELDS[form.value.card_type] || CARD_TYPE_FIELDS.custom
);

const placeholderText = computed(() => {
  const t = form.value.card_type;
  if (t === "character") {
    return "请输入角色的详细描述：身份/背景/关系/动机/能力/口癖/外貌（可选）等。写作时会作为设定依据。";
  }
  if (t === "worldview") {
    return "请输入世界观的详细描述：时代背景/地理/势力/超自然规则/关键设定等。";
  }
  if (t === "setting") {
    return "请输入设定的详细描述：道具/组织/规则/限制/重要信息等。";
  }
  if (t === "plot") {
    return "请输入剧情线的详细描述：阶段目标/关键事件/冲突/伏笔/走向等。";
  }
  return "请输入内容。你也可以在描述中写入关键词，便于 AI 续写时按需引用。";
});

function loadCard() {
  if (props.card) {
    form.value = {
      card_type: props.card.card_type as CardType,
      name: props.card.name || "",
      auto_update: props.card.auto_update,
    };
    try {
      const o = JSON.parse(props.card.content_json || "{}");
      // v0.2.3+: unified text field; keep backward compatibility for old structured JSON
      if (o && typeof o === "object") {
        const text =
          (o.text as string) ||
          (o.description as string) ||
          (o.rules as string) ||
          (o.summary as string) ||
          JSON.stringify(o, null, 2);
        formFields.value = { text: (text || "").toString() };
      } else {
        formFields.value = { text: String(o ?? "") };
      }
    } catch {
      formFields.value = { text: "" };
    }
  } else {
    form.value = {
      card_type: "character",
      name: "",
      auto_update: false,
    };
    formFields.value = { text: "" };
    try {
      const o = JSON.parse(defaultContentJson("character"));
      for (const k of Object.keys(o)) formFields.value[k] = o[k];
    } catch {}
  }
}

watch(
  () => [props.modelValue, props.card] as const,
  () => {
    if (props.modelValue) loadCard();
  },
  { immediate: true }
);

watch(
  () => form.value.card_type,
  (t) => {
    const fields = CARD_TYPE_FIELDS[t] || CARD_TYPE_FIELDS.custom;
    const next: Record<string, string> = {};
    for (const f of fields) next[f.key] = formFields.value[f.key] ?? "";
    formFields.value = next;
  }
);

function submit() {
  const content: Record<string, string> = {};
  for (const f of currentFields.value) content[f.key] = formFields.value[f.key] ?? "";
  emit("saved", {
    id: props.card?.id,
    novel_id: props.novelId,
    card_type: form.value.card_type,
    name: form.value.name,
    content_json: JSON.stringify(content, null, 2),
    auto_update: form.value.auto_update,
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
