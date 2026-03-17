<template>
  <el-dialog
    v-model="visible"
    title="卡片更新确认"
    width="860px"
    destroy-on-close
    append-to-body
    align-center
  >
    <div class="sub-title">
      AI 已根据最新正文生成了卡片更新建议。你可以查看新旧对比、编辑新内容，然后选择「覆盖」或「保留」。
    </div>

    <div v-if="items.length" class="list">
      <div v-for="it in items" :key="it.key" class="item">
        <div class="item-head">
          <div class="item-title">
            <span class="name">{{ it.name }}</span>
            <span class="meta">{{ typeLabel(it.card_type) }}</span>
            <span v-if="it.kind === 'new'" class="badge">新卡片</span>
            <span v-else class="badge badge-muted">更新</span>
          </div>
          <el-switch v-model="it.apply" active-text="覆盖" inactive-text="保留" />
        </div>

        <div class="diff">
          <div class="col">
            <div class="col-title">当前内容</div>
            <el-input
              v-model="it.oldText"
              type="textarea"
              :rows="6"
              readonly
              placeholder="（空）"
            />
          </div>
          <div class="col">
            <div class="col-title">建议内容（可编辑）</div>
            <el-input
              v-model="it.newText"
              type="textarea"
              :rows="6"
              :placeholder="placeholderByType(it.card_type)"
            />
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty">暂无需要确认的卡片更新</div>

    <template #footer>
      <div class="footer">
        <el-button @click="applyAll(true)">全部覆盖</el-button>
        <el-button @click="applyAll(false)">全部保留</el-button>
        <div class="spacer" />
        <el-button @click="visible = false">关闭</el-button>
        <el-button type="primary" :loading="saving" @click="save">应用所选</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { CARD_TYPE_LABELS } from "@/constants/cards";
import type { Card, CardType } from "@/types";
import { useNovelStore } from "@/stores/novel";
import { ElMessage } from "element-plus";

type Payload = {
  updates: { card_id: number; text: string }[];
  new_cards: { card_type: string; name: string; text: string; auto_update: boolean }[];
};

type Item = {
  key: string;
  kind: "update" | "new";
  apply: boolean;
  card_id?: number;
  card_type: CardType;
  name: string;
  oldText: string;
  newText: string;
  auto_update: boolean;
};

const props = defineProps<{
  modelValue: boolean;
  payload: Payload | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  applied: [];
}>();

const store = useNovelStore();
const saving = ref(false);
const items = ref<Item[]>([]);

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

function safeParseText(card?: Card | null): string {
  if (!card) return "";
  try {
    const o = JSON.parse(card.content_json || "{}");
    if (o && typeof o === "object") {
      return (
        (o.text as string) ||
        (o.description as string) ||
        (o.rules as string) ||
        (o.summary as string) ||
        JSON.stringify(o, null, 2)
      );
    }
    return String(o ?? "");
  } catch {
    return card.content_json || "";
  }
}

function typeLabel(t: CardType) {
  return CARD_TYPE_LABELS[t] ?? t;
}

function placeholderByType(t: CardType) {
  if (t === "character") return "角色详细描述：身份/背景/关系/动机/能力/口癖/外貌（可选）等";
  if (t === "worldview") return "世界观详细描述：时代背景/地理/势力/规则/关键设定等";
  if (t === "setting") return "设定详细描述：道具/组织/规则/限制/重要信息等";
  if (t === "plot") return "剧情线详细描述：阶段目标/关键事件/冲突/伏笔/走向等";
  return "请输入内容";
}

function applyAll(v: boolean) {
  for (const it of items.value) it.apply = v;
}

watch(
  () => [props.modelValue, props.payload, store.cards] as const,
  () => {
    if (!props.modelValue || !props.payload) return;
    const next: Item[] = [];
    for (const u of props.payload.updates || []) {
      const card = store.cards.find((c) => c.id === u.card_id);
      if (!card) continue;
      next.push({
        key: `u-${u.card_id}`,
        kind: "update",
        apply: true,
        card_id: u.card_id,
        card_type: card.card_type,
        name: card.name || "未命名",
        oldText: safeParseText(card),
        newText: u.text || "",
        auto_update: card.auto_update,
      });
    }
    for (const n of props.payload.new_cards || []) {
      const ct = (n.card_type as CardType) || "custom";
      next.push({
        key: `n-${ct}-${n.name}`,
        kind: "new",
        apply: true,
        card_type: ct,
        name: n.name || "未命名",
        oldText: "",
        newText: n.text || "",
        auto_update: !!n.auto_update,
      });
    }
    items.value = next;
  },
  { deep: true }
);

async function save() {
  if (!store.currentNovel) return;
  const toApply = items.value.filter((i) => i.apply && i.newText.trim());
  if (!toApply.length) {
    visible.value = false;
    return;
  }
  saving.value = true;
  try {
    for (const it of toApply) {
      if (it.kind === "update" && it.card_id != null) {
        await store.updateCard(it.card_id, {
          content_json: JSON.stringify({ text: it.newText.trim() }),
          auto_update: true,
        });
      }
      if (it.kind === "new") {
        await store.createCard({
          novel_id: store.currentNovel.id,
          card_type: it.card_type,
          name: it.name,
          content_json: JSON.stringify({ text: it.newText.trim() }),
          auto_update: it.auto_update,
        });
      }
    }
    ElMessage.success("已应用卡片更新");
    emit("applied");
    visible.value = false;
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.sub-title {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 10px;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.item {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.item-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.name {
  font-weight: 600;
}
.meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.5);
}
.badge-muted {
  opacity: 0.85;
}
.diff {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.col-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.footer {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
}
.spacer {
  flex: 1;
}
.empty {
  padding: 16px;
  color: var(--el-text-color-secondary);
}
</style>

