<template>
  <div class="left-panel">
    <!-- 小说家：固定标题 + 外框内约 3 条高度，内部滚动 -->
    <section class="section section--fixed">
      <div class="section-header">
        <span>小说家</span>
        <el-button type="primary" link class="add-btn" @click="openAuthorEditor(null)">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div class="section-frame">
        <div class="section-body section-body--authors">
          <ul class="author-list">
            <li
              v-for="a in authorStore.authors"
              :key="a.id"
              :class="{ active: authorStore.currentAuthorId === a.id }"
              @click="authorStore.setCurrentAuthor(a.id)"
              @contextmenu.prevent="(e) => openAuthorMenu(e, a)"
            >
              {{ a.name || "未命名" }}
            </li>
            <li v-if="!authorStore.authors.length" class="empty">暂无小说家，点击 + 新建</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- 小说列表：固定标题 + 外框内约 5 条高度，内部滚动 -->
    <section class="section section--fixed">
      <div class="section-header">
        <span>小说列表</span>
        <el-button type="primary" link class="add-btn" @click="handleAddNovel">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div class="section-frame">
        <div class="section-body section-body--novels">
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
        </div>
      </div>
    </section>

    <!-- 章节列表：固定标题 + 剩余空间外框，内部滚动 -->
    <section class="section section--fill">
      <div class="section-header">
        <span>章节列表</span>
        <el-button
          type="primary"
          link
          class="add-btn"
          :disabled="!store.currentNovel"
          @click="handleAddChapter"
        >
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div class="section-frame section-frame--fill">
        <div class="section-body section-body--chapters">
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
        </div>
      </div>
    </section>

    <el-dialog v-model="contextMenuVisible" title="操作" width="280px" :show-close="true" append-to-body align-center>
      <div class="context-menu-btns">
        <template v-if="contextTarget === 'novel'">
          <el-button text block @click="handleRenameNovel">重命名</el-button>
          <el-button text type="danger" block @click="handleDeleteNovel">删除小说</el-button>
        </template>
        <template v-else-if="contextTarget === 'chapter'">
          <el-button text block @click="handleEditChapter">编辑</el-button>
          <el-button text type="danger" block @click="handleDeleteChapter">删除章节</el-button>
        </template>
        <template v-else-if="contextTarget === 'author'">
          <el-button text block @click="handleEditAuthor">编辑</el-button>
          <el-button text type="danger" block @click="handleDeleteAuthor">删除</el-button>
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

    <ChapterEditDialog
      v-model="chapterEditVisible"
      :chapter="editingChapter"
      @saved="onChapterEdited"
    />

    <AuthorEditor
      v-model="authorEditorVisible"
      :author="editingAuthor"
      @saved="onAuthorSaved"
    />

    <NovelCreateDialog
      v-model="novelCreateVisible"
      @saved="onNovelCreated"
    />

    <ChapterCreateDialog
      v-model="chapterCreateVisible"
      :novel-id="store.currentNovel?.id ?? 0"
      :next-chapter-index="(store.chapters?.length ?? 0) + 1"
      @saved="onChapterCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { useNovelStore } from "@/stores/novel";
import { useAuthorStore } from "@/stores/author";
import type { Novel, Chapter, Author } from "@/types";
import { ElMessage, ElMessageBox } from "element-plus";
import AuthorEditor from "./AuthorEditor.vue";
import NovelCreateDialog from "./NovelCreateDialog.vue";
import ChapterCreateDialog from "./ChapterCreateDialog.vue";
import ChapterEditDialog from "./ChapterEditDialog.vue";

const store = useNovelStore();
const authorStore = useAuthorStore();
const contextTarget = ref<"novel" | "chapter" | "author" | null>(null);
const editingAuthor = ref<Author | null>(null);
const authorEditorVisible = ref(false);
const novelCreateVisible = ref(false);
const chapterCreateVisible = ref(false);
const chapterEditVisible = ref(false);
const editingChapter = ref<Chapter | null>(null);

onMounted(() => {
  authorStore.fetchAuthors();
});
const contextNovel = ref<Novel | null>(null);
const contextChapter = ref<Chapter | null>(null);
const contextAuthor = ref<Author | null>(null);
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
  contextAuthor.value = null;
  contextMenuVisible.value = true;
}

function openChapterMenu(_e: MouseEvent, c: Chapter) {
  contextTarget.value = "chapter";
  contextChapter.value = c;
  contextNovel.value = null;
  contextAuthor.value = null;
  contextMenuVisible.value = true;
}

function openAuthorMenu(_e: MouseEvent, a: Author) {
  contextTarget.value = "author";
  contextAuthor.value = a;
  contextNovel.value = null;
  contextChapter.value = null;
  contextMenuVisible.value = true;
}

function openAuthorEditor(a: Author | null) {
  editingAuthor.value = a;
  authorEditorVisible.value = true;
}

function onAuthorSaved(payload: { id?: number; name: string; style: string; format_rules: string }) {
  if (payload.id != null) {
    authorStore.updateAuthor(payload.id, {
      name: payload.name,
      style: payload.style,
      format_rules: payload.format_rules,
    });
  } else {
    authorStore.createAuthor({
      name: payload.name,
      style: payload.style,
      format_rules: payload.format_rules,
    });
  }
  ElMessage.success("已保存");
}

function handleEditAuthor() {
  contextMenuVisible.value = false;
  if (contextAuthor.value) {
    editingAuthor.value = contextAuthor.value;
    authorEditorVisible.value = true;
  }
  contextAuthor.value = null;
}

function handleDeleteAuthor() {
  contextMenuVisible.value = false;
  if (!contextAuthor.value) return;
  ElMessageBox.confirm("确定删除该小说家？", "确认删除", { type: "warning" })
    .then(() => {
      authorStore.deleteAuthor(contextAuthor.value!.id);
      contextAuthor.value = null;
      ElMessage.success("已删除");
    })
    .catch(() => {});
}

function handleAddNovel() {
  novelCreateVisible.value = true;
}

async function onNovelCreated(payload: { title: string; description: string; worldview: string }) {
  const novel = await store.createNovel({
    title: payload.title,
    description: payload.description || undefined,
  });
  if (novel && payload.worldview) {
    await store.createCard({
      novel_id: novel.id,
      card_type: "worldview",
      name: "世界观",
      content_json: JSON.stringify({ text: payload.worldview }),
    });
  }
  if (novel) store.selectNovel(novel);
  ElMessage.success("已创建小说");
}

function handleAddChapter() {
  if (store.currentNovel) chapterCreateVisible.value = true;
}

async function onChapterCreated(payload: {
  title: string;
  summary: string;
  target_words: number;
}) {
  if (!store.currentNovel) return;
  const chapter = await store.createChapter({
    title: payload.title,
    summary: payload.summary || undefined,
    target_words: payload.target_words || undefined,
  });
  if (chapter) store.selectChapter(chapter);
  ElMessage.success("已创建章节");
}

function handleRenameNovel() {
  contextMenuVisible.value = false;
  if (contextNovel.value) {
    renameInput.value = contextNovel.value.title || "";
    renameDialogVisible.value = true;
  }
}

function handleEditChapter() {
  contextMenuVisible.value = false;
  if (!contextChapter.value) return;
  editingChapter.value = contextChapter.value;
  chapterEditVisible.value = true;
}

async function onChapterEdited(payload: { id: number; title: string; summary: string; target_words: number }) {
  await store.updateChapter(payload.id, {
    title: payload.title,
    summary: payload.summary || null,
    target_words: payload.target_words || null,
  });
  ElMessage.success("已保存");
  editingChapter.value = null;
  contextChapter.value = null;
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
  gap: 12px;
  height: 100%;
  min-height: 0;
}
.section {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.section--fixed {
  flex: 0 0 auto;
}
.section--fill {
  flex: 1 1 0;
  min-height: 0;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 2px 0 8px;
  font-weight: 600;
  font-size: 13px;
}
.section-frame {
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.section-frame:hover {
  border-color: rgba(255, 255, 255, 0.75);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}
.section-frame--fill {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.section-body {
  overflow-y: auto;
  overflow-x: hidden;
  padding: 6px 4px 6px 6px;
  -webkit-overflow-scrolling: touch;
}
.section-body--authors {
  height: 132px;
}
.section-body--novels {
  height: 220px;
}
.section-body--chapters {
  flex: 1;
  min-height: 0;
  height: 100%;
}
/* iOS 风格滚动条：细、圆角、顺滑 */
.section-body::-webkit-scrollbar {
  width: 6px;
}
.section-body::-webkit-scrollbar-track {
  background: transparent;
}
.section-body::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.18);
  border-radius: 3px;
}
.section-body::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.28);
}
.section-body::-webkit-scrollbar-thumb:active {
  background: rgba(0, 0, 0, 0.35);
}

.novel-list,
.chapter-list,
.author-list {
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
.author-list li {
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s cubic-bezier(0.2, 0, 0, 1);
}
.author-list li:hover {
  background: var(--el-fill-color-light);
  transform: translateX(2px);
}
.author-list li.active {
  background: var(--el-color-primary-light-9);
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
