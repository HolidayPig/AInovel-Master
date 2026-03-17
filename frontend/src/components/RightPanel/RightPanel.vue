<template>
  <div class="right-panel">
    <div v-if="!store.currentNovel" class="empty-hint">请先选择或新建小说</div>
    <template v-else>
      <div class="section-header row">
        <span>小说属性卡片</span>
        <el-button type="primary" link class="add-btn add-btn-with-text" @click="openEditor(null)">
          <el-icon><Plus /></el-icon>
          新建
        </el-button>
      </div>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="角色" name="character" />
        <el-tab-pane label="世界观" name="worldview" />
        <el-tab-pane label="设定" name="setting" />
        <el-tab-pane label="全部" name="all" />
      </el-tabs>
      <el-scrollbar class="card-list-scroll">
        <div class="card-list">
          <div
            v-for="card in filteredCards"
            :key="card.id"
            class="card-item"
            @click="openEditor(card)"
          >
            <div class="card-head row">
              <span class="card-name">{{ card.name || "未命名" }}</span>
              <el-icon
                class="card-delete"
                @click.stop="handleDeleteCard(card)"
              >
                <Delete />
              </el-icon>
            </div>
            <div class="card-preview">{{ cardPreview(card) }}</div>
            <div v-if="card.auto_update" class="card-badge">自动更新</div>
          </div>
          <div v-if="!filteredCards.length" class="empty">暂无卡片，点击「新建」添加</div>
        </div>
      </el-scrollbar>
    </template>

    <CardEditor
      v-model="editorVisible"
      :novel-id="store.currentNovel?.id ?? 0"
      :card="editingCard"
      @saved="onCardSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Plus, Delete } from "@element-plus/icons-vue";
import type { Card } from "@/types";
import { useNovelStore } from "@/stores/novel";
import { ElMessage, ElMessageBox } from "element-plus";
import CardEditor from "./CardEditor.vue";

const store = useNovelStore();
const activeTab = ref("all");
const editorVisible = ref(false);
const editingCard = ref<Card | null>(null);

const filteredCards = computed(() => {
  const list = store.cards;
  if (activeTab.value === "all") return list;
  return list.filter((c) => c.card_type === activeTab.value);
});

function openEditor(card: Card | null) {
  if (!store.currentNovel) return;
  editingCard.value = card;
  editorVisible.value = true;
}

function onCardSaved(payload: {
  id?: number;
  novel_id: number;
  card_type: string;
  name: string;
  content_json: string;
  auto_update: boolean;
}) {
  if (payload.id != null) {
    store.updateCard(payload.id, {
      name: payload.name,
      content_json: payload.content_json,
      auto_update: payload.auto_update,
    });
  } else {
    store.createCard({
      novel_id: payload.novel_id,
      card_type: payload.card_type,
      name: payload.name,
      content_json: payload.content_json,
      auto_update: payload.auto_update,
    });
  }
  ElMessage.success("已保存");
}

function handleDeleteCard(card: Card) {
  ElMessageBox.confirm("确定删除该卡片？", "确认删除", { type: "warning" })
    .then(() => {
      store.deleteCard(card.id);
      ElMessage.success("已删除");
    })
    .catch(() => {});
}

function cardPreview(card: Card): string {
  try {
    const o = JSON.parse(card.content_json || "{}");
    if (o && typeof o === "object") {
      const text =
        (o.text as string) ||
        (o.description as string) ||
        (o.rules as string) ||
        (o.summary as string) ||
        "";
      const s = (text || JSON.stringify(o)).toString();
      return s.slice(0, 80) + (s.length > 80 ? "..." : "");
    }
    const s = String(o ?? "");
    return s.slice(0, 80) + (s.length > 80 ? "..." : "");
  } catch {
    return card.content_json?.slice(0, 80) || "";
  }
}
</script>

<style scoped>
.right-panel {
  padding: 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.empty-hint {
  color: var(--el-text-color-secondary);
  padding: 16px;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-header {
  font-weight: 600;
  margin-bottom: 8px;
}
.card-list-scroll {
  flex: 1;
  min-height: 0;
}
.card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card-item {
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 14px;
  font-size: 13px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s cubic-bezier(0.2, 0, 0, 1);
}
.card-item:hover {
  border-color: rgba(64, 158, 255, 0.4);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  transform: translateX(-2px);
  background: rgba(255, 255, 255, 0.55);
}
.card-head {
  margin-bottom: 4px;
}
.card-name {
  font-weight: 500;
}
.card-delete {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
}
.card-delete:hover {
  color: var(--el-color-danger);
}
.card-preview {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-badge {
  margin-top: 4px;
  font-size: 11px;
  color: var(--el-color-primary);
}
.empty {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  padding: 16px;
}
</style>
