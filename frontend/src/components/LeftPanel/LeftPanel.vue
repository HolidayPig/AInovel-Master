<template>
  <div class="left-panel">
    <section class="section">
      <div class="section-header">
        <span>小说列表</span>
        <el-button type="primary" link @click="handleAddNovel">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <el-scrollbar height="200">
        <ul class="novel-list">
          <li
            v-for="n in store.novels"
            :key="n.id"
            :class="{ active: store.currentNovel?.id === n.id }"
            @click="store.selectNovel(n)"
            @contextmenu.prevent="(e) => openNovelMenu(e, n)"
          >
            {{ n.title || "未命名" }}
          </li>
          <li v-if="!store.novels.length" class="empty">暂无小说，点击 + 新建</li>
        </ul>
      </el-scrollbar>
    </section>
    <section class="section">
      <div class="section-header">
        <span>章节列表</span>
        <el-button
          type="primary"
          link
          :disabled="!store.currentNovel"
          @click="handleAddChapter"
        >
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <el-scrollbar class="chapter-scroll">
        <ul
          class="chapter-list"
          @dragover.prevent
          @drop="onChapterDrop"
        >
          <li
            v-for="(c, index) in store.chapters"
            :key="c.id"
            class="chapter-item"
            :class="{ active: store.currentChapter?.id === c.id }"
            :draggable="true"
            @click="store.selectChapter(c)"
            @contextmenu.prevent="(e) => openChapterMenu(e, c)"
            @dragstart="(e) => onChapterDragStart(e, index)"
            @dragend="(e) => ((e.currentTarget as HTMLElement).style.opacity = '1')"
          >
            <span class="chapter-drag-handle" title="拖拽排序">⋮⋮</span>
            {{ c.title || "未命名章节" }}
          </li>
          <li v-if="store.currentNovel && !store.chapters.length" class="empty">
            暂无章节，点击 + 新建
          </li>
        </ul>
      </el-scrollbar>
    </section>

    <el-dialog v-model="contextMenuVisible" title="操作" width="280px" :show-close="true" append-to-body align-center>
      <div class="context-menu-btns">
        <template v-if="contextTarget === 'novel'">
          <el-button text block @click="handleRenameNovel">重命名</el-button>
          <el-button text type="danger" block @click="handleDeleteNovel">删除小说</el-button>
        </template>
        <template v-else-if="contextTarget === 'chapter'">
          <el-button text block @click="handleRenameChapter">重命名</el-button>
          <el-button text type="danger" block @click="handleDeleteChapter">删除章节</el-button>
        </template>
      </div>
    </el-dialog>

    <el-dialog v-model="renameDialogVisible" title="重命名" width="400px" append-to-body align-center @close="renameInput = ''">
      <el-input
        v-model="renameInput"
        :placeholder="renamePlaceholder"
        @keydown.enter="submitRename"
      />
      <template #footer>
        <el-button @click="renameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRename">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { useNovelStore } from "@/stores/novel";
import type { Novel, Chapter } from "@/types";
import { ElMessage, ElMessageBox } from "element-plus";

const store = useNovelStore();
const contextTarget = ref<"novel" | "chapter" | null>(null);
const contextNovel = ref<Novel | null>(null);
const contextChapter = ref<Chapter | null>(null);
const contextMenuVisible = ref(false);
const renameDialogVisible = ref(false);
const renameInput = ref("");

const renamePlaceholder = computed(() =>
  contextTarget.value === "novel" ? "小说标题" : "章节标题"
);

function openNovelMenu(_e: MouseEvent, n: Novel) {
  contextTarget.value = "novel";
  contextNovel.value = n;
  contextChapter.value = null;
  contextMenuVisible.value = true;
}

function openChapterMenu(_e: MouseEvent, c: Chapter) {
  contextTarget.value = "chapter";
  contextChapter.value = c;
  contextNovel.value = null;
  contextMenuVisible.value = true;
}

function handleAddNovel() {
  store.createNovel();
}

function handleAddChapter() {
  if (store.currentNovel) store.createChapter();
}

function handleRenameNovel() {
  contextMenuVisible.value = false;
  if (contextNovel.value) {
    renameInput.value = contextNovel.value.title || "";
    renameDialogVisible.value = true;
  }
}

function handleRenameChapter() {
  contextMenuVisible.value = false;
  if (contextChapter.value) {
    renameInput.value = contextChapter.value.title || "";
    renameDialogVisible.value = true;
  }
}

async function submitRename() {
  const name = renameInput.value.trim();
  if (!name) return;
  if (contextTarget.value === "novel" && contextNovel.value) {
    await store.updateNovel(contextNovel.value.id, { title: name });
    ElMessage.success("已保存");
  }
  if (contextTarget.value === "chapter" && contextChapter.value) {
    await store.updateChapter(contextChapter.value.id, { title: name });
    ElMessage.success("已保存");
  }
  renameDialogVisible.value = false;
  contextNovel.value = null;
  contextChapter.value = null;
}

function handleDeleteNovel() {
  contextMenuVisible.value = false;
  if (!contextNovel.value) return;
  ElMessageBox.confirm("确定删除该小说及其所有章节？", "确认删除", {
    type: "warning",
  }).then(() => {
    store.deleteNovel(contextNovel.value!.id);
    contextNovel.value = null;
    ElMessage.success("已删除");
  }).catch(() => {});
}

function handleDeleteChapter() {
  contextMenuVisible.value = false;
  if (!contextChapter.value) return;
  ElMessageBox.confirm("确定删除该章节？", "确认删除", {
    type: "warning",
  }).then(() => {
    store.deleteChapter(contextChapter.value!.id);
    contextChapter.value = null;
    ElMessage.success("已删除");
  }).catch(() => {});
}

let draggedChapterIndex = -1;

function onChapterDragStart(e: DragEvent, index: number) {
  draggedChapterIndex = index;
  (e.target as HTMLElement).style.opacity = "0.5";
  e.dataTransfer!.effectAllowed = "move";
  e.dataTransfer!.setData("text/plain", String(index));
}

async function onChapterDrop(e: DragEvent) {
  e.preventDefault();
  if (draggedChapterIndex < 0 || !store.chapters.length) return;
  const target = (e.target as HTMLElement).closest("li.chapter-item");
  if (!target) return;
  const toIndex = Array.from(document.querySelectorAll("li.chapter-item")).indexOf(target);
  if (toIndex < 0 || toIndex === draggedChapterIndex) {
    draggedChapterIndex = -1;
    return;
  }
  const chapters = [...store.chapters];
  const [moved] = chapters.splice(draggedChapterIndex, 1);
  chapters.splice(toIndex, 0, moved);
  store.chapters.splice(0, store.chapters.length, ...chapters);
  for (let i = 0; i < chapters.length; i++) {
    if (chapters[i].sort_order !== i) {
      await store.updateChapter(chapters[i].id, { sort_order: i });
    }
  }
  draggedChapterIndex = -1;
  ElMessage.success("顺序已更新");
}
</script>

<style scoped>
.left-panel {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-weight: 600;
}
.novel-list,
.chapter-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.novel-list li,
.chapter-list li {
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s cubic-bezier(0.2, 0, 0, 1);
}
.novel-list li:hover,
.chapter-list li:hover {
  background: var(--el-fill-color-light);
  transform: translateX(2px);
}
.novel-list li.active,
.chapter-list li.active {
  background: var(--el-color-primary-light-9);
}
.chapter-scroll {
  flex: 1;
  min-height: 120px;
}
.empty {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.context-menu-btns {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chapter-drag-handle {
  margin-right: 6px;
  color: var(--el-text-color-placeholder);
  cursor: grab;
  font-size: 12px;
  user-select: none;
}
.chapter-item {
  display: flex;
  align-items: center;
}
</style>
