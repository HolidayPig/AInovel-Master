<template>
  <div class="right-panel">
    <div v-if="!store.currentNovel" class="empty-hint">请先选择或新建小说</div>
    <template v-else>
      <div class="section-header row">
        <span>小说属性卡片</span>
        <div class="header-actions">
          <el-button class="panel-pill" title="从当前章节引入卡片" @click="openIntroDialog">
            <el-icon><Upload /></el-icon>
            Import
          </el-button>
          <el-button class="panel-pill panel-pill--primary" @click="openEditor(null)">
            <el-icon><Plus /></el-icon>
            New
          </el-button>
        </div>
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
            <div class="card-actions">
              <el-button
                class="card-act"
                size="small"
                :loading="updatingCardId === card.id"
                @click.stop="handleCardUpdate(card)"
              >
                <el-icon><Refresh /></el-icon>
                Sync
              </el-button>
              <el-button
                class="card-act card-act--web"
                size="small"
                :loading="searchingCardId === card.id"
                @click.stop="handleSearchOnline(card)"
              >
                <el-icon><Search /></el-icon>
                Web
              </el-button>
            </div>
          </div>
          <div v-if="!filteredCards.length" class="empty">暂无卡片，点击 New 添加</div>
        </div>
      </el-scrollbar>
      <div class="panel-footer">
        <el-button
          type="primary"
          :loading="refreshingAll"
          :disabled="!filteredCards.length"
          @click="handleRefreshAll"
        >
          <el-icon class="footer-icon"><RefreshRight /></el-icon>
          Refresh all
        </el-button>
      </div>
    </template>

    <CardIntroDialog
      v-model="introVisible"
      :novel-id="store.currentNovel?.id ?? 0"
      :chapter-id="store.currentChapter?.id ?? 0"
      :settings-id="getSettingsId() ?? 0"
      @added="onCardsApplied"
    />
    <CardUpdateConfirmDialog
      v-model="cardUpdateVisible"
      :payload="cardUpdatePayload"
      @applied="onCardsApplied"
    />
    <CardEditor
      v-model="editorVisible"
      :novel-id="store.currentNovel?.id ?? 0"
      :card="editingCard"
      :updating="editingCard !== null && updatingCardId === editingCard.id"
      :searching="editingCard !== null && searchingCardId === editingCard.id"
      @request-update="onEditorRequestUpdate"
      @request-search-online="onEditorRequestSearchOnline"
      @saved="onCardSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Plus, Delete, Upload, Refresh, Search, RefreshRight } from "@element-plus/icons-vue";
import type { Card } from "@/types";
import { useNovelStore } from "@/stores/novel";
import { useSettingsStore } from "@/stores/settings";
import { ElMessage, ElMessageBox } from "element-plus";
import CardEditor from "./CardEditor.vue";
import CardIntroDialog from "./CardIntroDialog.vue";
import CardUpdateConfirmDialog from "./CardUpdateConfirmDialog.vue";
import * as cardApi from "@/api/cards";
import { useAiProgressStore } from "@/stores/aiProgress";

const store = useNovelStore();
const aiProgress = useAiProgressStore();
const settingsStore = useSettingsStore();
const activeTab = ref("all");
const editorVisible = ref(false);
const editingCard = ref<Card | null>(null);
const refreshingAll = ref(false);
const updatingCardId = ref<number | null>(null);
const searchingCardId = ref<number | null>(null);
const introVisible = ref(false);
const cardUpdateVisible = ref(false);
const cardUpdatePayload = ref<{
  updates: { card_id: number; text: string }[];
  new_cards: { card_type: string; name: string; text: string; auto_update: boolean }[];
} | null>(null);

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
}) {
  if (payload.id != null) {
    store.updateCard(payload.id, {
      name: payload.name,
      content_json: payload.content_json,
    });
  } else {
    store.createCard({
      novel_id: payload.novel_id,
      card_type: payload.card_type,
      name: payload.name,
      content_json: payload.content_json,
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

function getSettingsId(): number | null {
  return settingsStore.currentId ?? settingsStore.current()?.id ?? null;
}

function openIntroDialog() {
  if (!store.currentNovel) {
    ElMessage.warning("请先选择小说");
    return;
  }
  if (!store.currentChapter) {
    ElMessage.warning("请先在左侧选择当前章节，引入将分析该章正文");
    return;
  }
  if (!getSettingsId()) {
    ElMessage.warning("请先在设置中配置 API Key 和模型");
    return;
  }
  introVisible.value = true;
}

async function handleRefreshAll() {
  const novel = store.currentNovel;
  const settingsId = getSettingsId();
  if (!novel || !settingsId) {
    ElMessage.warning("请先在设置中配置 API Key 和模型");
    return;
  }
  refreshingAll.value = true;
  const n = filteredCards.value.length;
  aiProgress.start("一键更新卡片", {
    phase: "processing",
    detail: `正在根据小说正文批量刷新 ${n} 张卡片的描述，请稍候…`,
  });
  try {
    const res = await cardApi.refreshAllCards(novel.id, settingsId);
    await store.fetchCards();
    aiProgress.setDetail(`已完成 ${res.data.updated} 张卡片的描述更新。`);
    aiProgress.finishSuccess(650);
    ElMessage.success(`已更新 ${res.data.updated} 张卡片`);
  } catch (e) {
    aiProgress.finishError();
    ElMessage.error(String(e));
  } finally {
    refreshingAll.value = false;
  }
}

async function handleCardUpdate(card: Card) {
  const novel = store.currentNovel;
  const settingsId = getSettingsId();
  if (!novel || !settingsId) {
    ElMessage.warning("请先在设置中配置 API Key 和模型");
    return;
  }
  updatingCardId.value = card.id;
  aiProgress.start("更新卡片", {
    phase: "processing",
    detail: `正在结合小说正文为「${card.name || "未命名"}」生成新的卡片描述…`,
  });
  try {
    const res = await cardApi.refreshOneCardSuggestion(card.id, novel.id, settingsId);
    aiProgress.setDetail("已生成建议描述，请在确认弹窗中查看。");
    aiProgress.finishSuccess(550);
    cardUpdatePayload.value = {
      updates: [{ card_id: card.id, text: res.data.new_text }],
      new_cards: [],
    };
    cardUpdateVisible.value = true;
  } catch (e) {
    aiProgress.finishError();
    ElMessage.error(String(e));
  } finally {
    updatingCardId.value = null;
  }
}

function onEditorRequestUpdate() {
  if (editingCard.value) handleCardUpdate(editingCard.value);
}

function onEditorRequestSearchOnline() {
  if (editingCard.value) handleSearchOnline(editingCard.value);
}

function onCardsApplied() {
  store.fetchCards();
}

async function handleSearchOnline(card: Card) {
  const settingsId = getSettingsId();
  if (!settingsId) {
    ElMessage.warning("请先在设置中配置 API Key 和模型");
    return;
  }
  searchingCardId.value = card.id;
  aiProgress.start("联网查询", {
    phase: "querying",
    detail: `正在联网检索与「${card.name || "该卡片"}」相关的资料并整理为描述…`,
  });
  try {
    const res = await cardApi.searchOnlineCard(card.id, settingsId);
    aiProgress.setDetail("检索完成，请在确认弹窗中查看合并后的描述。");
    aiProgress.finishSuccess(550);
    cardUpdatePayload.value = {
      updates: [{ card_id: card.id, text: res.data.new_text }],
      new_cards: [],
    };
    cardUpdateVisible.value = true;
  } catch (e) {
    aiProgress.finishError();
    ElMessage.error(String(e));
  } finally {
    searchingCardId.value = null;
  }
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
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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
.empty {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  padding: 16px;
}
.card-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.panel-footer {
  flex-shrink: 0;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}
.panel-footer .el-button {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.footer-icon {
  font-size: 16px;
}
</style>
