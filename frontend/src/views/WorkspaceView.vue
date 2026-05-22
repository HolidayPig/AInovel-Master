<template>
  <div class="workspace-view" v-if="store.currentNovel">
    <div class="workspace-header">
      <div>
        <h2>{{ store.currentNovel.title || "未命名小说" }}</h2>
        <p>{{ store.currentNovel.description || "暂无简介" }}</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadWorkspace">刷新</el-button>
    </div>

    <div class="stat-grid">
      <div class="stat-item">
        <span>总字数</span>
        <strong>{{ stats?.total_words ?? 0 }}</strong>
      </div>
      <div class="stat-item">
        <span>章节</span>
        <strong>{{ stats?.done_chapter_count ?? 0 }}/{{ stats?.chapter_count ?? 0 }}</strong>
      </div>
      <div class="stat-item">
        <span>目标字数</span>
        <strong>{{ stats?.target_words_total ?? 0 }}</strong>
      </div>
      <div class="stat-item">
        <span>完成率</span>
        <strong>{{ stats?.completion_rate ?? 0 }}%</strong>
      </div>
    </div>

    <section class="workspace-section">
      <div class="section-head">
        <span>全书大纲</span>
        <el-button size="small" type="primary" :loading="savingOutline" @click="saveOutline">保存大纲</el-button>
      </div>
      <el-input
        v-model="outlineDraft"
        type="textarea"
        :rows="5"
        placeholder="这里用于维护全书结构、阶段目标、高潮与结局。Outline 生成后会自动写入这里。"
      />
    </section>

    <section class="workspace-section">
      <div class="section-head">
        <span>章节结构</span>
        <el-tag effect="plain">{{ chapters.length }} 章</el-tag>
      </div>
      <el-table :data="chapters" size="small" class="workspace-table" max-height="280">
        <el-table-column prop="title" label="章节" min-width="150" />
        <el-table-column prop="summary" label="梗概" min-width="220" show-overflow-tooltip />
        <el-table-column label="字数" width="120">
          <template #default="{ row }">{{ row.word_count }} / {{ row.target_words || "-" }}</template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <el-select v-model="row.status" size="small" @change="updateChapterStatus(row)">
              <el-option label="草稿" value="drafting" />
              <el-option label="修订中" value="reviewing" />
              <el-option label="完成" value="done" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <div class="workspace-split">
      <section class="workspace-section">
        <div class="section-head">
          <span>时间线</span>
          <div class="head-actions">
            <el-button size="small" :disabled="!store.currentChapter" :loading="extractingTimeline" @click="extractTimeline">
              AI 提取
            </el-button>
            <el-button size="small" type="primary" @click="openTimelineEditor(null)">新增事件</el-button>
          </div>
        </div>
        <div v-if="!timeline.length" class="empty-inline">暂无时间线事件</div>
        <div v-else class="timeline-list">
          <div v-for="event in timeline" :key="event.id" class="timeline-item">
            <div class="timeline-main">
              <span class="event-time">{{ event.event_time || "未标注时间" }}</span>
              <strong>{{ event.title }}</strong>
              <p>{{ event.summary }}</p>
              <small v-if="event.characters">角色：{{ event.characters }}</small>
            </div>
            <div class="item-actions">
              <el-button size="small" text @click="openTimelineEditor(event)">编辑</el-button>
              <el-button size="small" text type="danger" @click="deleteTimeline(event.id)">删除</el-button>
            </div>
          </div>
        </div>
      </section>

      <section class="workspace-section">
        <div class="section-head">
          <span>一致性检查</span>
          <div class="head-actions">
            <el-select v-model="checkScope" size="small" class="scope-select">
              <el-option label="当前章节" value="chapter" />
              <el-option label="最近 5 章" value="recent" />
              <el-option label="全书" value="all" />
            </el-select>
            <el-button size="small" type="primary" :loading="checking" @click="runCheck">开始检查</el-button>
          </div>
        </div>
        <div v-if="!checks.length" class="empty-inline">暂无未解决问题</div>
        <div v-else class="check-list">
          <div v-for="check in checks" :key="check.id" class="check-item" :class="`severity-${check.severity}`">
            <div>
              <el-tag size="small" :type="severityType(check.severity)">{{ severityLabel(check.severity) }}</el-tag>
              <strong>{{ check.message }}</strong>
              <p>{{ check.suggestion || "暂无建议" }}</p>
            </div>
            <el-button size="small" text type="success" @click="resolveCheck(check.id)">标记解决</el-button>
          </div>
        </div>
      </section>
    </div>

    <el-dialog v-model="timelineDialogVisible" title="时间线事件" width="520px" append-to-body align-center>
      <el-form label-position="top">
        <el-form-item label="标题"><el-input v-model="timelineForm.title" /></el-form-item>
        <el-form-item label="故事内时间"><el-input v-model="timelineForm.event_time" placeholder="例如 第一天夜里 / 三年后" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="timelineForm.summary" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="相关角色"><el-input v-model="timelineForm.characters" placeholder="逗号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="timelineDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTimeline">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="candidateDialogVisible" title="AI 提取的时间线候选" width="680px" append-to-body align-center>
      <div v-if="!timelineCandidates.length" class="empty-inline">没有可写入的候选事件</div>
      <div v-else class="candidate-list">
        <el-checkbox-group v-model="selectedCandidateIndexes">
          <div v-for="(item, index) in timelineCandidates" :key="index" class="candidate-item">
            <el-checkbox :label="index">
              <strong>{{ item.title }}</strong>
              <span>{{ item.event_time }}</span>
            </el-checkbox>
            <p>{{ item.summary }}</p>
          </div>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="candidateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyTimelineCandidates">写入选中事件</el-button>
      </template>
    </el-dialog>
  </div>
  <div v-else class="workspace-empty">请选择或新建小说后进入工作台</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { useNovelStore } from "@/stores/novel";
import { useSettingsStore } from "@/stores/settings";
import type { ConsistencyCheck, NovelStats, TimelineEvent, TimelineEventCandidate, WorkspaceChapter } from "@/types";
import * as novelApi from "@/api/novels";
import * as chapterApi from "@/api/chapters";
import * as timelineApi from "@/api/timeline";
import * as consistencyApi from "@/api/consistency";

const store = useNovelStore();
const settingsStore = useSettingsStore();
const loading = ref(false);
const savingOutline = ref(false);
const extractingTimeline = ref(false);
const checking = ref(false);
const stats = ref<NovelStats | null>(null);
const chapters = ref<WorkspaceChapter[]>([]);
const timeline = ref<TimelineEvent[]>([]);
const checks = ref<ConsistencyCheck[]>([]);
const outlineDraft = ref("");
const checkScope = ref<"chapter" | "recent" | "all">("recent");

const timelineDialogVisible = ref(false);
const editingTimelineId = ref<number | null>(null);
const timelineForm = ref({ title: "", event_time: "", summary: "", characters: "" });
const candidateDialogVisible = ref(false);
const timelineCandidates = ref<TimelineEventCandidate[]>([]);
const selectedCandidateIndexes = ref<number[]>([]);

const novelId = computed(() => store.currentNovel?.id ?? 0);

onMounted(() => loadWorkspace());
watch(() => store.currentNovel?.id, () => loadWorkspace());

async function loadWorkspace() {
  if (!novelId.value) return;
  loading.value = true;
  try {
    const res = await novelApi.getWorkspace(novelId.value);
    stats.value = res.data.stats;
    chapters.value = res.data.chapters;
    timeline.value = res.data.recent_timeline_events;
    checks.value = res.data.unresolved_checks;
    outlineDraft.value = res.data.novel.outline || "";
    store.currentNovel = res.data.novel;
    const idx = store.novels.findIndex((n) => n.id === res.data.novel.id);
    if (idx >= 0) store.novels[idx] = res.data.novel;
  } finally {
    loading.value = false;
  }
}

async function saveOutline() {
  if (!store.currentNovel) return;
  savingOutline.value = true;
  try {
    const res = await novelApi.updateNovel(store.currentNovel.id, { outline: outlineDraft.value });
    store.currentNovel = res.data;
    ElMessage.success("大纲已保存");
  } finally {
    savingOutline.value = false;
  }
}

async function updateChapterStatus(row: WorkspaceChapter) {
  await chapterApi.updateChapter(row.id, { status: row.status });
  await store.fetchChapters();
  await loadWorkspace();
}

function openTimelineEditor(event: TimelineEvent | null) {
  editingTimelineId.value = event?.id ?? null;
  timelineForm.value = {
    title: event?.title || "",
    event_time: event?.event_time || "",
    summary: event?.summary || "",
    characters: event?.characters || "",
  };
  timelineDialogVisible.value = true;
}

async function saveTimeline() {
  if (!store.currentNovel) return;
  const payload = {
    novel_id: store.currentNovel.id,
    chapter_id: store.currentChapter?.id ?? null,
    title: timelineForm.value.title.trim() || "未命名事件",
    event_time: timelineForm.value.event_time.trim(),
    summary: timelineForm.value.summary.trim(),
    characters: timelineForm.value.characters.trim(),
    sort_order: timeline.value.length,
  };
  if (editingTimelineId.value) {
    await timelineApi.updateTimelineEvent(editingTimelineId.value, payload);
  } else {
    await timelineApi.createTimelineEvent(payload);
  }
  timelineDialogVisible.value = false;
  await loadWorkspace();
  ElMessage.success("时间线已更新");
}

async function deleteTimeline(id: number) {
  await ElMessageBox.confirm("确定删除该时间线事件？", "确认删除", { type: "warning" });
  await timelineApi.deleteTimelineEvent(id);
  await loadWorkspace();
}

async function extractTimeline() {
  if (!store.currentNovel || !store.currentChapter) {
    ElMessage.warning("请先选择一个章节");
    return;
  }
  const settingsId = settingsStore.currentId ?? settingsStore.current()?.id;
  if (!settingsId) {
    ElMessage.warning("请先配置模型");
    return;
  }
  extractingTimeline.value = true;
  try {
    const res = await timelineApi.extractTimelineEvents({
      novel_id: store.currentNovel.id,
      chapter_id: store.currentChapter.id,
      settings_id: settingsId,
    });
    timelineCandidates.value = res.data;
    selectedCandidateIndexes.value = res.data.map((_, i) => i);
    candidateDialogVisible.value = true;
  } finally {
    extractingTimeline.value = false;
  }
}

async function applyTimelineCandidates() {
  if (!store.currentNovel || !store.currentChapter) return;
  for (const index of selectedCandidateIndexes.value) {
    const item = timelineCandidates.value[index];
    if (!item) continue;
    await timelineApi.createTimelineEvent({
      novel_id: store.currentNovel.id,
      chapter_id: store.currentChapter.id,
      title: item.title,
      event_time: item.event_time,
      summary: item.summary,
      characters: item.characters,
      sort_order: timeline.value.length + index,
    });
  }
  candidateDialogVisible.value = false;
  await loadWorkspace();
  ElMessage.success("已写入时间线");
}

async function runCheck() {
  if (!store.currentNovel) return;
  const settingsId = settingsStore.currentId ?? settingsStore.current()?.id;
  if (!settingsId) {
    ElMessage.warning("请先配置模型");
    return;
  }
  if (checkScope.value === "chapter" && !store.currentChapter) {
    ElMessage.warning("请先选择当前章节");
    return;
  }
  checking.value = true;
  try {
    const res = await novelApi.runConsistencyCheck(store.currentNovel.id, {
      settings_id: settingsId,
      scope: checkScope.value,
      chapter_id: store.currentChapter?.id ?? null,
    });
    checks.value = [...res.data, ...checks.value];
    ElMessage.success(res.data.length ? `发现 ${res.data.length} 条问题` : "未发现明显问题");
    await loadWorkspace();
  } finally {
    checking.value = false;
  }
}

async function resolveCheck(id: number) {
  await consistencyApi.updateConsistencyCheck(id, { resolved: true });
  checks.value = checks.value.filter((c) => c.id !== id);
}

function severityType(severity: string) {
  if (severity === "high") return "danger";
  if (severity === "low") return "info";
  return "warning";
}

function severityLabel(severity: string) {
  if (severity === "high") return "高";
  if (severity === "low") return "低";
  return "中";
}
</script>

<style scoped>
.workspace-view {
  padding: 18px;
  height: 100%;
  overflow-y: auto;
}
.workspace-header,
.section-head,
.head-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.workspace-header h2 {
  margin: 0 0 6px;
  font-size: 22px;
}
.workspace-header p {
  margin: 0;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0;
}
.stat-item,
.workspace-section {
  border: 1px solid rgba(255, 255, 255, 0.65);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.48);
  backdrop-filter: blur(12px);
}
.stat-item {
  padding: 12px;
}
.stat-item span {
  display: block;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.stat-item strong {
  font-size: 22px;
}
.workspace-section {
  padding: 14px;
  margin-bottom: 12px;
}
.section-head {
  margin-bottom: 12px;
  font-weight: 600;
}
.workspace-split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}
.workspace-table {
  border-radius: 8px;
}
.timeline-list,
.check-list,
.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.timeline-item,
.check-item,
.candidate-item {
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid var(--el-border-color-lighter);
}
.timeline-item,
.check-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.timeline-main p,
.check-item p,
.candidate-item p {
  margin: 6px 0 0;
  color: var(--el-text-color-regular);
  line-height: 1.5;
}
.event-time {
  display: block;
  margin-bottom: 4px;
  color: var(--el-color-primary);
  font-size: 12px;
}
.item-actions {
  display: flex;
  flex-shrink: 0;
}
.scope-select {
  width: 110px;
}
.empty-inline,
.workspace-empty {
  color: var(--el-text-color-secondary);
  text-align: center;
  padding: 24px;
}
@media (max-width: 1100px) {
  .stat-grid,
  .workspace-split {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
