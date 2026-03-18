<template>
  <el-dialog
    v-model="visible"
    title="从章节引入卡片"
    width="720px"
    destroy-on-close
    append-to-body
    align-center
    class="card-intro-dialog"
  >
    <p v-if="!chapterId" class="hint">请先在左侧选择当前要分析的章节。</p>
    <template v-else>
      <p class="hint">
        将根据<strong>当前章节正文</strong>识别可建档的角色、设定、世界观等元素。默认<strong>折叠</strong>仅显示名称，点击条目展开编辑描述；勾选后点「添加选中项」写入右侧卡片栏。
      </p>
      <div v-if="rows.length > 1 && !loading" class="collapse-tools">
        <el-button text type="primary" size="small" @click="expandAll">全部展开</el-button>
        <el-button text type="primary" size="small" @click="collapseAll">全部折叠</el-button>
      </div>
      <div v-loading="loading" class="body intro-scroll">
        <template v-if="!loading && rows.length === 0">
          <p class="empty">
            未生成可勾选条目。请先确认<strong>中间编辑区本章已有正文</strong>（空章节无法分析）；若有正文仍为空，请点击关闭后<strong>再试一次「引入」</strong>，或检查 API/网络。
            后端已加强识别并在失败时从正文自动切分兜底条目，正常情况应至少出现若干条待整理卡片。
          </p>
        </template>
        <el-collapse v-else v-model="activeNames" class="intro-collapse">
          <el-collapse-item
            v-for="(row, idx) in rows"
            :key="idx"
            :name="String(idx)"
          >
            <template #title>
              <span class="collapse-title" @click.stop @mousedown.stop>
                <el-checkbox v-model="row.selected" @click.stop @mousedown.stop />
                <span class="t-name" :title="row.name">{{ row.name }}</span>
                <el-tag size="small" type="info" class="t-tag">{{ typeLabel(row.card_type) }}</el-tag>
              </span>
            </template>
            <div v-if="row.reason" class="reason">识别理由：{{ row.reason }}</div>
            <div class="type-row">
              <span class="type-label">类型</span>
              <el-select v-model="row.card_type" style="width: 140px">
                <el-option label="角色" value="character" />
                <el-option label="世界观" value="worldview" />
                <el-option label="设定" value="setting" />
                <el-option label="剧情线" value="plot" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </div>
            <el-input
              v-model="row.text"
              type="textarea"
              :rows="10"
              placeholder="卡片描述（建议保留【定位】【要点】【关系】【写作提示】结构）"
            />
          </el-collapse-item>
        </el-collapse>
      </div>
    </template>
    <template #footer>
      <el-button v-if="rows.length" @click="selectAll(true)">全选</el-button>
      <el-button v-if="rows.length" @click="selectAll(false)">全不选</el-button>
      <el-button @click="visible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="adding"
        :disabled="!chapterId || !selectedCount"
        @click="addSelected"
      >
        添加选中项（{{ selectedCount }}）
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { CARD_TYPE_LABELS } from "@/constants/cards";
import type { CardType } from "@/types";
import * as cardApi from "@/api/cards";
import { ElMessage } from "element-plus";
import { useAiProgressStore } from "@/stores/aiProgress";

const props = defineProps<{
  modelValue: boolean;
  novelId: number;
  chapterId: number;
  settingsId: number;
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  added: [];
}>();

type Row = {
  name: string;
  card_type: CardType;
  reason: string;
  text: string;
  selected: boolean;
};

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const loading = ref(false);
const aiProgress = useAiProgressStore();
const adding = ref(false);
const rows = ref<Row[]>([]);
const activeNames = ref<string[]>([]);

const selectedCount = computed(() => rows.value.filter((r) => r.selected).length);

function typeLabel(t: string) {
  return CARD_TYPE_LABELS[t as CardType] ?? t;
}

function selectAll(v: boolean) {
  for (const r of rows.value) r.selected = v;
}

function expandAll() {
  activeNames.value = rows.value.map((_, i) => String(i));
}

function collapseAll() {
  activeNames.value = [];
}

watch(
  () => props.modelValue,
  async (v) => {
    if (!v) {
      rows.value = [];
      activeNames.value = [];
      return;
    }
    if (!props.chapterId || !props.novelId || !props.settingsId) return;
    loading.value = true;
    rows.value = [];
    aiProgress.start("引入卡片", {
      phase: "processing",
      detail: "正在阅读本章正文并调用模型识别角色、世界观与设定等元素…",
    });
    try {
      const res = await cardApi.suggestCardsFromChapter(
        props.chapterId,
        props.novelId,
        props.settingsId
      );
      const list = res.data.candidates || [];
      aiProgress.setDetail(`已识别到 ${list.length} 个候选，请在弹窗中勾选并编辑。`);
      aiProgress.finishSuccess(600);
      rows.value = list.map((c) => ({
        name: c.name,
        card_type: (["character", "worldview", "setting", "plot", "custom"].includes(c.card_type)
          ? c.card_type
          : "custom") as CardType,
        reason: c.reason || "",
        text: c.text || "",
        selected: list.length <= 5,
      }));
      /* 默认全部折叠，仅显示名称，避免多条同时撑满屏导致顶部被裁切 */
      activeNames.value = list.length === 1 ? ["0"] : [];
    } catch (e) {
      aiProgress.setDetail(String(e));
      aiProgress.finishError();
      ElMessage.error(String(e));
    } finally {
      loading.value = false;
    }
  }
);

async function addSelected() {
  const picked = rows.value.filter((r) => r.selected && r.name.trim() && r.text.trim());
  if (!picked.length) {
    ElMessage.warning("请至少勾选一项且填写描述");
    return;
  }
  adding.value = true;
  try {
    for (const r of picked) {
      await cardApi.createCard({
        novel_id: props.novelId,
        card_type: r.card_type,
        name: r.name.trim(),
        content_json: JSON.stringify({ text: r.text.trim() }),
        auto_update: false,
      });
    }
    ElMessage.success(`已添加 ${picked.length} 张卡片`);
    emit("added");
    visible.value = false;
  } catch (e) {
    ElMessage.error(String(e));
  } finally {
    adding.value = false;
  }
}
</script>

<style scoped>
.hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0 0 8px;
  line-height: 1.5;
}
.collapse-tools {
  margin-bottom: 8px;
  display: flex;
  gap: 4px;
}
.body {
  min-height: 100px;
}
/* 列表区独立滚动，保证任意条目在视口内可滚到 */
.intro-scroll {
  max-height: min(52vh, 520px);
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  -webkit-overflow-scrolling: touch;
}
.intro-scroll::-webkit-scrollbar {
  width: 8px;
}
.intro-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}
.empty {
  color: var(--el-text-color-secondary);
  padding: 16px 0;
}
.collapse-title {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
  padding-right: 8px;
}
.t-name {
  font-weight: 600;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}
.t-tag {
  flex-shrink: 0;
}
.reason {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}
.type-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.type-label {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.intro-collapse :deep(.el-collapse-item__header) {
  height: auto;
  min-height: 44px;
  line-height: 1.35;
  padding: 10px 12px 10px 8px;
  align-items: center;
}
.intro-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.intro-collapse :deep(.el-collapse-item__content) {
  padding-bottom: 12px;
  padding-top: 4px;
}
.intro-collapse :deep(.el-textarea__inner) {
  max-height: 40vh;
}
</style>

<style>
/* 弹窗整体限高，避免超出视口后顶部被裁且无法滚到 */
.card-intro-dialog.el-dialog {
  display: flex;
  flex-direction: column;
  max-height: 92vh;
  margin-top: 4vh !important;
}
.card-intro-dialog .el-dialog__header {
  flex-shrink: 0;
  padding-bottom: 8px;
}
.card-intro-dialog .el-dialog__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding-top: 0;
}
.card-intro-dialog .el-dialog__footer {
  flex-shrink: 0;
}
</style>
