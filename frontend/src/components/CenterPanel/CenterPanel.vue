<template>
  <div class="center-panel">
    <ProgressBar
      :visible="progressVisible"
      :phase="progressPhase"
      :bar-color="progressBarColor"
    />
    <div v-if="!store.currentChapter" class="empty-hint">
      请从左侧选择或新建章节后编辑
    </div>
    <template v-else>
      <div class="editor-area">
        <div class="editor-area-content">
          <NovelEditor
            :key="store.currentChapter.id"
            v-model="localContent"
            class="editor-inner"
          />
          <div v-if="streamingText || showConfirmBar" class="stream-output">
          <div class="stream-label">{{ showConfirmBar ? "生成完毕，请确认" : "AI 续写中..." }}</div>
          <div class="stream-text">{{ streamingText }}</div>
          <div v-if="showConfirmBar" class="confirm-bar">
            <el-button type="primary" @click="acceptGenerated">接受</el-button>
            <el-button @click="regenerate">重新生成</el-button>
          </div>
          </div>
        </div>
      </div>
      <div class="prompt-area">
        <div class="prompt-inner">
          <el-input
            v-model="prompt"
            type="textarea"
            :rows="2"
            placeholder="输入续写提示，按 Ctrl+Enter 或点击发送"
            @keydown.ctrl.enter.prevent="handleSend"
          />
          <div class="prompt-tools">
            <el-switch
              v-if="canWebSearch"
              v-model="webSearchThisTime"
              size="small"
              inline-prompt
              active-text="联网"
              inactive-text="不联网"
            />
          </div>
          <el-button type="primary" :loading="generating" @click="handleSend">发送</el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
 import { ref, watch, computed } from "vue";
import { useNovelStore } from "@/stores/novel";
import { useSettingsStore } from "@/stores/settings";
import { useAuthorStore } from "@/stores/author";
import NovelEditor from "./NovelEditor.vue";
import ProgressBar from "./ProgressBar.vue";
import { streamGenerate } from "@/api/ai";
import { ElMessage } from "element-plus";

const store = useNovelStore();
const settingsStore = useSettingsStore();
const authorStore = useAuthorStore();
const localContent = ref("");
const prompt = ref("");
const generating = ref(false);
const streamingText = ref("");
const progressVisible = ref(false);
const progressPhase = ref<"prepare" | "thinking" | "writing" | "done" | "error">("prepare");
const progressBarColor = ref({ from: "#409eff", to: "#79bbff" });
const showConfirmBar = ref(false);
const webSearchThisTime = ref(false);
const canWebSearch = computed(() => {
  const cur = settingsStore.current();
  if (!cur) return false;
  return cur.provider === "grok" || cur.provider === "xai";
});
let lastGenerateParams: {
  settings_id: number;
  novel_id: number;
  chapter_id: number;
  author_id: number | null;
  context: string;
  prompt: string;
} | null = null;
let doneHideTimer: ReturnType<typeof setTimeout> | null = null;

const PROGRESS_COLORS = [
  { from: "#409eff", to: "#79bbff" },
  { from: "#67c23a", to: "#95d475" },
  { from: "#e6a23c", to: "#f0c78a" },
  { from: "#f56c6c", to: "#f89898" },
  { from: "#909399", to: "#b1b3b8" },
  { from: "#9c27b0", to: "#ce93d8" },
  { from: "#00bcd4", to: "#80deea" },
  { from: "#ff9800", to: "#ffb74d" },
];
function pickProgressColor() {
  return PROGRESS_COLORS[Math.floor(Math.random() * PROGRESS_COLORS.length)];
}

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
  progressBarColor.value = pickProgressColor();
  progressVisible.value = true;
  if (doneHideTimer) clearTimeout(doneHideTimer);
  let userPrompt = prompt.value.trim();
  prompt.value = "";
  if (chapter.summary || (chapter.target_words && chapter.target_words > 0)) {
    const parts: string[] = [];
    if (chapter.summary) parts.push("【本章梗概】\n" + chapter.summary);
    if (chapter.target_words && chapter.target_words > 0)
      parts.push("【目标字数】约 " + chapter.target_words + " 字");
    parts.push("【续写提示】\n" + (userPrompt || "请继续写下去。"));
    userPrompt = parts.join("\n\n");
  } else {
    userPrompt = userPrompt || "请继续写下去。";
  }
  const params = {
    settings_id: settingsId,
    novel_id: novel.id,
    chapter_id: chapter.id,
    author_id: authorStore.currentAuthorId,
    context: stripHtml(localContent.value),
    prompt: userPrompt,
    web_search_enabled: canWebSearch.value ? webSearchThisTime.value : undefined,
  };
  lastGenerateParams = params;
  const tThinking = setTimeout(() => {
    if (progressPhase.value === "prepare") progressPhase.value = "thinking";
  }, 400);
  try {
    await streamGenerate(
      params,
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
          showConfirmBar.value = false;
          ElMessage.error(ev.message);
          doneHideTimer = setTimeout(() => {
            progressVisible.value = false;
          }, 1200);
        }
        if (ev.type === "done") {
          clearTimeout(tThinking);
          progressPhase.value = "done";
          generating.value = false;
          showConfirmBar.value = true;
          doneHideTimer = setTimeout(() => {
            progressVisible.value = false;
          }, 300);
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

function acceptGenerated() {
  const appended = streamingText.value;
  if (appended && store.currentChapter) {
    const escaped = htmlEscape(appended).replace(/\n/g, "</p><p>");
    const newBlock = "<p>" + escaped + "</p>";
    localContent.value = (localContent.value || "").trimEnd() + newBlock;
    store.updateChapter(store.currentChapter.id, { content: localContent.value });
  }
  streamingText.value = "";
  showConfirmBar.value = false;
  lastGenerateParams = null;
  ElMessage.success("已并入正文");
}

function regenerate() {
  if (!lastGenerateParams) return;
  streamingText.value = "";
  showConfirmBar.value = false;
  progressBarColor.value = pickProgressColor();
  progressVisible.value = true;
  progressPhase.value = "prepare";
  generating.value = true;
  const params = { ...lastGenerateParams };
  streamGenerate(params, (ev) => {
    if (ev.type === "delta") {
      if (progressPhase.value !== "writing") progressPhase.value = "writing";
      streamingText.value += ev.text;
    }
    if (ev.type === "error") {
      progressPhase.value = "error";
      generating.value = false;
      ElMessage.error(ev.message);
      progressVisible.value = false;
    }
    if (ev.type === "done") {
      progressPhase.value = "done";
      generating.value = false;
      showConfirmBar.value = true;
      progressVisible.value = false;
    }
  });
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
  overflow-y: auto;
}
.editor-area-content {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.editor-inner {
  flex: 1;
  min-height: 180px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 14px;
  overflow: auto;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04);
}
.prompt-area {
  flex-shrink: 0;
  padding: 12px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}
.prompt-inner {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.prompt-tools {
  display: flex;
  align-items: center;
  padding-bottom: 2px;
}
.prompt-inner .el-input {
  flex: 1;
}
.stream-output {
  flex: 0 0 auto;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.stream-output .stream-text {
  max-height: 320px;
  overflow-y: auto;
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
.confirm-bar {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  display: flex;
  gap: 8px;
}
</style>
