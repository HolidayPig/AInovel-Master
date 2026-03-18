<template>
  <div class="center-panel">
    <div v-if="!store.currentChapter" class="empty-hint">
      请从左侧选择或新建章节后编辑
    </div>
    <template v-else>
      <div v-if="store.currentChapter?.summary" class="chapter-summary-bar">
        <span class="chapter-summary-label">本章梗概</span>
        <span class="chapter-summary-text">{{ store.currentChapter.summary }}</span>
      </div>
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
            <el-button type="primary" @click="acceptGenerated">Apply</el-button>
            <el-button @click="regenerate">Regenerate</el-button>
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
          <el-button type="primary" :loading="generating" class="send-btn" @click="handleSend">
            Send
          </el-button>
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
import { streamGenerate } from "@/api/ai";
import { useAiProgressStore } from "@/stores/aiProgress";
import { ElMessage } from "element-plus";

const store = useNovelStore();
const settingsStore = useSettingsStore();
const authorStore = useAuthorStore();
const aiProgress = useAiProgressStore();
const localContent = ref("");
const prompt = ref("");
const generating = ref(false);
const streamingText = ref("");
const showConfirmBar = ref(false);
const webSearchThisTime = ref(false);
const canWebSearch = computed(() => {
  const cur = settingsStore.current();
  if (!cur) return false;
  if (cur.provider === "grok" || cur.provider === "xai") return true;
  try {
    const o = JSON.parse(cur.extra_config_json || "{}");
    return !!(o.supports_web_search ?? o.web_search_supported ?? o.enable_web_search);
  } catch {
    return false;
  }
});
let lastGenerateParams: {
  settings_id: number;
  novel_id: number;
  chapter_id: number;
  author_id: number | null;
  context: string;
  prompt: string;
  web_search_enabled?: boolean;
} | null = null;
let lastDetailThrottle = 0;

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
  lastDetailThrottle = 0;
  const useWeb = canWebSearch.value && webSearchThisTime.value;
  aiProgress.start("续写发送", {
    phase: "prepare",
    detail: useWeb
      ? "已开启联网：模型将先检索网络再续写，耗时可能稍长…"
      : "正在注入本章梗概、目标字数与相关小说卡片…",
  });
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
  lastGenerateParams = { ...params, web_search_enabled: params.web_search_enabled };
  const tThinking = setTimeout(() => {
    if (aiProgress.phase === "prepare") {
      aiProgress.setPhase("thinking", useWeb ? "联网检索与推理中，尚未输出正文…" : "模型正在构思下文，请稍候…");
    }
  }, 450);
  try {
    await streamGenerate(
      params,
      (ev) => {
        if (ev.type === "status") {
          // 后端实时状态：读取/组装/联网/等待首 token 等
          aiProgress.setPhase(ev.phase as any, ev.detail || "");
          return;
        }
        if (ev.type === "delta") {
          clearTimeout(tThinking);
          streamingText.value += ev.text;
          if (aiProgress.phase !== "writing") {
            aiProgress.setPhase("writing");
          }
          const now = Date.now();
          if (now - lastDetailThrottle > 380) {
            aiProgress.appendWritingPreview(streamingText.value);
            lastDetailThrottle = now;
          }
        }
        if (ev.type === "error") {
          clearTimeout(tThinking);
          aiProgress.setDetail(ev.message || "生成失败");
          aiProgress.finishError();
          generating.value = false;
          showConfirmBar.value = false;
          ElMessage.error(ev.message);
        }
        if (ev.type === "done") {
          clearTimeout(tThinking);
          aiProgress.setDetail("本段生成完毕，请在下方预览并点击「接受」并入正文。");
          aiProgress.finishSuccess(550);
          generating.value = false;
          showConfirmBar.value = true;
        }
      }
    );
  } catch (e) {
    clearTimeout(tThinking);
    aiProgress.setDetail(String(e));
    aiProgress.finishError();
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
  lastDetailThrottle = 0;
  const useWeb = !!lastGenerateParams.web_search_enabled;
  aiProgress.start("重新生成", {
    phase: "prepare",
    detail: useWeb ? "重新联网检索并生成…" : "使用上次提示与上下文重新生成…",
  });
  generating.value = true;
  const params = { ...lastGenerateParams };
  const tThinking = setTimeout(() => {
    if (aiProgress.phase === "prepare") {
      aiProgress.setPhase("thinking", useWeb ? "联网检索与推理中…" : "模型重新构思中…");
    }
  }, 450);
  streamGenerate(params, (ev) => {
    if (ev.type === "status") {
      aiProgress.setPhase(ev.phase as any, ev.detail || "");
      return;
    }
    if (ev.type === "delta") {
      clearTimeout(tThinking);
      streamingText.value += ev.text;
      if (aiProgress.phase !== "writing") aiProgress.setPhase("writing");
      const now = Date.now();
      if (now - lastDetailThrottle > 380) {
        aiProgress.appendWritingPreview(streamingText.value);
        lastDetailThrottle = now;
      }
    }
    if (ev.type === "error") {
      clearTimeout(tThinking);
      aiProgress.setDetail(ev.message || "失败");
      aiProgress.finishError();
      generating.value = false;
      ElMessage.error(ev.message);
    }
    if (ev.type === "done") {
      clearTimeout(tThinking);
      aiProgress.setDetail("生成完毕，请确认后接受。");
      aiProgress.finishSuccess(500);
      generating.value = false;
      showConfirmBar.value = true;
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
.chapter-summary-bar {
  flex-shrink: 0;
  margin: 12px 16px 0;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  font-size: 13px;
  line-height: 1.55;
  max-height: 120px;
  overflow-y: auto;
}
.chapter-summary-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 6px;
}
.chapter-summary-text {
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
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
.send-btn {
  min-width: 88px;
  font-weight: 600;
  letter-spacing: 0.04em;
}
</style>
