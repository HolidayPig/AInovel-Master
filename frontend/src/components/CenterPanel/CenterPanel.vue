<template>
  <div class="center-panel">
    <ProgressCapsule
      :visible="progressVisible"
      :phase="progressPhase"
    />
    <div v-if="!store.currentChapter" class="empty-hint">
      请从左侧选择或新建章节后编辑
    </div>
    <template v-else>
      <div class="editor-area">
        <NovelEditor
          :key="store.currentChapter.id"
          v-model="localContent"
          class="editor-inner"
        />
        <div v-if="streamingText" class="stream-output">
          <div class="stream-label">AI 续写中...</div>
          <div class="stream-text">{{ streamingText }}</div>
        </div>
      </div>
      <div class="prompt-area">
        <el-input
          v-model="prompt"
          type="textarea"
          :rows="2"
          placeholder="输入续写提示，按 Ctrl+Enter 或点击发送"
          @keydown.ctrl.enter.prevent="handleSend"
        />
        <el-button type="primary" :loading="generating" @click="handleSend">发送</el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useNovelStore } from "@/stores/novel";
import { useSettingsStore } from "@/stores/settings";
import NovelEditor from "./NovelEditor.vue";
import ProgressCapsule from "./ProgressCapsule.vue";
import { streamGenerate } from "@/api/ai";
import { ElMessage } from "element-plus";

const store = useNovelStore();
const settingsStore = useSettingsStore();
const localContent = ref("");
const prompt = ref("");
const generating = ref(false);
const streamingText = ref("");
const progressVisible = ref(false);
const progressPhase = ref<"prepare" | "thinking" | "writing" | "done" | "error">("prepare");
let doneHideTimer: ReturnType<typeof setTimeout> | null = null;

function stripHtml(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return (div.textContent || "").trim();
}

function htmlEscape(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

watch(
  () => store.currentChapter,
  (ch) => {
    localContent.value = ch?.content ?? "";
  },
  { immediate: true }
);

watch(localContent, (val) => {
  if (store.currentChapter && store.currentChapter.content !== val) {
    debouncedSave(val);
  }
});

let saveTimer: ReturnType<typeof setTimeout> | null = null;
function debouncedSave(content: string) {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    if (store.currentChapter) store.updateChapter(store.currentChapter.id, { content });
    saveTimer = null;
  }, 800);
}

async function handleSend() {
  if (generating.value || !prompt.value.trim()) return;
  const novel = store.currentNovel;
  const chapter = store.currentChapter;
  if (!novel || !chapter) return;
  const settingsId = settingsStore.currentId ?? settingsStore.current()?.id;
  if (!settingsId) {
    ElMessage.warning("请先在设置中配置 API Key 和模型");
    return;
  }
  generating.value = true;
  streamingText.value = "";
  progressPhase.value = "prepare";
  progressVisible.value = true;
  if (doneHideTimer) clearTimeout(doneHideTimer);
  const userPrompt = prompt.value.trim();
  prompt.value = "";
  const tThinking = setTimeout(() => {
    if (progressPhase.value === "prepare") progressPhase.value = "thinking";
  }, 400);
  try {
    await streamGenerate(
      {
        settings_id: settingsId,
        novel_id: novel.id,
        chapter_id: chapter.id,
        context: stripHtml(localContent.value),
        prompt: userPrompt,
      },
      (ev) => {
        if (ev.type === "delta") {
          clearTimeout(tThinking);
          if (progressPhase.value !== "writing") progressPhase.value = "writing";
          streamingText.value += ev.text;
        }
        if (ev.type === "error") {
          clearTimeout(tThinking);
          progressPhase.value = "error";
          generating.value = false;
          ElMessage.error(ev.message);
          doneHideTimer = setTimeout(() => {
            progressVisible.value = false;
          }, 1200);
        }
        if (ev.type === "done") {
          clearTimeout(tThinking);
          progressPhase.value = "done";
          const appended = streamingText.value;
          streamingText.value = "";
          generating.value = false;
          if (appended) {
            const escaped = htmlEscape(appended).replace(/\n/g, "</p><p>");
            const newBlock = "<p>" + escaped + "</p>";
            localContent.value = (localContent.value || "").trimEnd() + newBlock;
            if (store.currentChapter) {
              store.updateChapter(store.currentChapter.id, { content: localContent.value });
            }
          }
          doneHideTimer = setTimeout(() => {
            progressVisible.value = false;
          }, 1000);
        }
      }
    );
  } catch (e) {
    clearTimeout(tThinking);
    progressPhase.value = "error";
    progressVisible.value = true;
    doneHideTimer = setTimeout(() => {
      progressVisible.value = false;
    }, 1200);
    ElMessage.error(String(e));
    generating.value = false;
    streamingText.value = "";
  }
}
</script>

<style scoped>
.center-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.empty-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
}
.editor-area {
  flex: 1;
  padding: 16px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.editor-inner {
  flex: 1;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: auto;
}
.prompt-area {
  padding: 12px 16px;
  border-top: 1px solid var(--el-border-color-lighter);
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.prompt-area .el-input {
  flex: 1;
}
.stream-output {
  margin-top: 12px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  border: 1px dashed var(--el-border-color);
}
.stream-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.stream-text {
  white-space: pre-wrap;
  line-height: 1.7;
  font-size: 14px;
}
</style>
