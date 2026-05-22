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
      <el-form-item label="标签">
        <el-input v-model="form.tags" placeholder="逗号分隔，例如 主角,皇城,伏笔" />
      </el-form-item>
      <el-form-item label="重要度">
        <el-segmented v-model="form.importance" :options="importanceOptions" />
      </el-form-item>
      <el-alert
        v-if="isEdit"
        :title="referenceHint"
        type="info"
        :closable="false"
        show-icon
        class="reference-hint"
      />
      <el-alert
        v-if="isEdit"
        :title="aiSuggestionHint"
        type="success"
        :closable="false"
        show-icon
        class="reference-hint"
      />
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
    </el-form>
    <template #footer>
      <div class="footer-row">
        <div class="footer-left">
          <template v-if="isEdit">
            <el-button
              class="card-act"
              size="small"
              :loading="props.updating"
              @click="emit('requestUpdate')"
            >
              <el-icon><Refresh /></el-icon>
              Sync
            </el-button>
            <el-button
              class="card-act card-act--web"
              size="small"
              :loading="props.searching"
              @click="emit('requestSearchOnline')"
            >
              <el-icon><Search /></el-icon>
              Web
            </el-button>
          </template>
        </div>
        <div class="footer-right">
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" @click="submit">保存</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { Refresh, Search } from "@element-plus/icons-vue";
import { CARD_TYPE_LABELS, CARD_TYPE_FIELDS, defaultContentJson } from "@/constants/cards";
import type { Card, CardType } from "@/types";
import { useNovelStore } from "@/stores/novel";

const props = defineProps<{
  modelValue: boolean;
  novelId: number;
  card: Card | null;
  updating?: boolean;
  searching?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  close: [];
  requestUpdate: [];
  requestSearchOnline: [];
  saved: [
    payload: {
      id?: number;
      novel_id: number;
      card_type: string;
      name: string;
      content_json: string;
      tags: string;
      importance: number;
    }
  ];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const store = useNovelStore();
const isEdit = computed(() => !!props.card);

const form = ref({
  card_type: "character" as CardType,
  name: "",
  tags: "",
  importance: 2,
});

const formFields = ref<Record<string, string>>({});

const currentFields = computed(
  () => CARD_TYPE_FIELDS[form.value.card_type] || CARD_TYPE_FIELDS.custom
);

const importanceOptions = [
  { label: "低", value: 1 },
  { label: "中", value: 2 },
  { label: "高", value: 3 },
];

const referenceHint = computed(() => {
  if (!props.card?.last_referenced_at) return "该卡片暂未被 AI 续写引用。";
  const chapter = store.chapters.find((c) => c.id === props.card?.last_referenced_chapter_id);
  return `最近被 AI 引用：${chapter?.title || `章节 #${props.card.last_referenced_chapter_id || "-"}`} · ${new Date(props.card.last_referenced_at).toLocaleString()}`;
});

const aiSuggestionHint = computed(() => {
  const card = props.card;
  const chapter = store.currentChapter;
  if (!card || !chapter) return "AI 引用建议：选择章节后，会根据当前正文提示这张卡片是否值得注入续写。";
  const chapterText = `${chapter.title || ""} ${chapter.summary || ""} ${chapter.content || ""}`;
  const normalizedChapter = normalizeForMatch(chapterText);
  const tags = splitTags(card.tags);
  const matched = [card.name || "", ...tags].filter((token) => {
    const t = normalizeForMatch(token);
    return t.length >= 2 && normalizedChapter.includes(t);
  });
  if (matched.length) {
    return `AI 引用建议：当前章节提到了「${matched.slice(0, 3).join("、")}」，续写时建议优先注入这张卡片。`;
  }
  if ((card.importance || 2) === 3) return "AI 引用建议：这是一张高重要度卡片，即使当前章节未直接点名，也适合作为关键设定兜底参考。";
  if (card.card_type === "worldview" || card.card_type === "setting") return "AI 引用建议：世界观/设定卡可作为无明确匹配时的基础规则参考。";
  return "AI 引用建议：当前章节未明显命中名称或标签，可补充标签来提高续写注入准确度。";
});

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

function normalizeForMatch(s: string) {
  return (s || "").replace(/\s+/g, "").toLowerCase();
}

function splitTags(tags?: string) {
  return (tags || "").split(/[,，；;、\s]+/).map((t) => t.trim()).filter(Boolean);
}

function loadCard() {
  if (props.card) {
    form.value = {
      card_type: props.card.card_type as CardType,
      name: props.card.name || "",
      tags: props.card.tags || "",
      importance: props.card.importance || 2,
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
      tags: "",
      importance: 2,
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
  () => props.card?.content_json,
  () => {
    if (props.modelValue && props.card) loadCard();
  }
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
    tags: form.value.tags,
    importance: form.value.importance,
  });
  visible.value = false;
  emit("close");
}
</script>

<style scoped>
.footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  flex-wrap: wrap;
  gap: 8px;
}
.footer-left {
  display: flex;
  gap: 8px;
}
.footer-right {
  display: flex;
  gap: 8px;
}
.reference-hint {
  margin-bottom: 14px;
}
</style>
