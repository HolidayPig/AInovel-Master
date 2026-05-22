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
      <div class="chapter-toolbar">
        <div class="word-stats">
          <span>正文 {{ bodyWordCount }} 字</span>
          <span v-if="store.currentChapter.target_words">目标 {{ store.currentChapter.target_words }} 字</span>
        </div>
        <el-button
          class="outline-generate-btn"
          type="primary"
          plain
          :loading="generating"
          :disabled="!store.currentChapter.summary"
          @click="generateFromSummary"
        >
          根据本章梗概生成
        </el-button>
      </div>
      <div class="editor-area">
        <div class="editor-area-content">
          <NovelEditor
            :key="store.currentChapter.id"
            v-model="localContent"
            class="editor-inner"
          />
          <div v-if="streamingText || showConfirmBar" class="stream-output">
            <div class="stream-head">
              <div>
                <div class="stream-label">{{ showConfirmBar ? "生成完毕，请确认" : "AI 生成中..." }}</div>
                <div class="stream-count">生成 {{ generatedWordCount }} 字</div>
              </div>
              <div v-if="showConfirmBar" class="confirm-bar">
                <el-button type="primary" @click="acceptGenerated">接受</el-button>
                <el-button @click="regenerate">重新生成</el-button>
              </div>
            </div>
            <div class="stream-text">{{ streamingText }}</div>
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
          <el-button v-if="generating" type="danger" plain class="stop-btn" @click="stopGeneration">
            停止
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
const bodyWordCount = computed(() => countWords(stripHtml(localContent.value)));
const generatedWordCount = computed(() => countWords(streamingText.value));
let lastGenerateParams: {
  settings_id: number;
  novel_id: number;
  chapter_id: number;
  author_id: number | null;
  context: string;
  prompt: string;
  target_words?: number | null;
  generation_mode?: "continue" | "chapter_from_summary";
  web_search_enabled?: boolean;
} | null = null;
let lastDetailThrottle = 0;
let abortController: AbortController | null = null;
let stoppedByUser = false;

function stripHtml(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return (div.textContent || "").trim();
}

function countWords(text: string): number {
  const s = (text || "").trim();
  if (!s) return 0;
  const chinese = s.match(/[\u4e00-\u9fff]/g)?.length || 0;
  const words = s.replace(/[\u4e00-\u9fff]/g, " ").match(/[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*/g)?.length || 0;
  return chinese + words;
}

function limitTailText(text: string, max = 12000): string {
  const s = (text || "").trim();
  if (s.length <= max) return s;
  return "……（已省略更早正文）\n" + s.slice(-max);
}

function htmlEscape(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function sanitizeGeneratedText(text: string): string {
  const metaWords = /(下一[章节段]|后续|提纲|大纲|描写|写作|说明|注[:：]|作者|读者|本章将|可以继续|建议|如果需要|扩展|总结|以上|目标字数|字数)/;
  return (text || "")
    .replace(/^[ \t]*(?:#{1,6}\s*)?(?:正文|小说正文|生成正文)[:：]?[ \t]*$/gim, "")
    .split(/\n/)
    .map((line) => line.trimEnd())
    .filter((line) => {
      const t = line.trim();
      if (!t) return true;
      if (/^[（(【\[][^）)】\]]+[）)】\]]$/.test(t) && metaWords.test(t)) return false;
      if (/^(?:注[:：]|说明[:：]|下一[章节段]|后续|写作提示|作者提示|剧情提示)/.test(t)) return false;
      if (metaWords.test(t) && /不超过|接下来|下一步|下一[章节段]|可以|建议|将会|应当/.test(t)) return false;
      return true;
    })
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
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

async function runStreamOnce(params: NonNullable<typeof lastGenerateParams>) {
  let ok = true;
  let done = false;
  const tThinking = setTimeout(() => {
    if (aiProgress.phase === "prepare") {
      aiProgress.setPhase("thinking", params.web_search_enabled ? "联网检索与推理中，尚未输出正文…" : "模型正在构思下文，请稍候…");
    }
  }, 450);
  try {
    abortController = new AbortController();
    await streamGenerate(params, (ev) => {
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
        ok = false;
        aiProgress.setDetail(ev.message || "生成失败");
        aiProgress.finishError();
        ElMessage.error(ev.message);
      }
      if (ev.type === "done") {
        clearTimeout(tThinking);
        done = true;
      }
    }, abortController.signal);
  } catch (e) {
    clearTimeout(tThinking);
    if (stoppedByUser || (e instanceof DOMException && e.name === "AbortError")) {
      ok = false;
      aiProgress.setDetail("已停止生成，可接受当前已有内容或重新生成。");
      aiProgress.finishError();
    } else {
      ok = false;
      aiProgress.setDetail(String(e));
      aiProgress.finishError();
      ElMessage.error(String(e));
    }
  } finally {
    abortController = null;
  }
  streamingText.value = sanitizeGeneratedText(streamingText.value);
  return ok && done;
}

async function startGeneration(userPrompt: string, taskName = "续写发送", mode: "continue" | "chapter_from_summary" = "continue") {
  if (generating.value) return;
  const novel = store.currentNovel;
  const chapter = store.currentChapter;
  if (!novel || !chapter) return;
  const settingsId = settingsStore.currentId ?? settingsStore.current()?.id;
  if (!settingsId) {
    ElMessage.warning("请先在设置中配置 API Key 和模型");
    return;
  }
  userPrompt = (userPrompt || "").trim();
  if (!userPrompt) {
    ElMessage.warning("请先输入续写提示，或使用本章梗概生成");
    return;
  }
  generating.value = true;
  stoppedByUser = false;
  streamingText.value = "";
  showConfirmBar.value = false;
  lastDetailThrottle = 0;
  const useWeb = canWebSearch.value && webSearchThisTime.value;
  aiProgress.start(taskName, {
    phase: "prepare",
    detail: useWeb
      ? "已开启联网：模型将先检索网络再续写，耗时可能稍长…"
      : "正在注入本章梗概、目标字数与相关小说卡片…",
  });
  userPrompt = userPrompt || "请继续写下去。";
  const params = {
    settings_id: settingsId,
    novel_id: novel.id,
    chapter_id: chapter.id,
    author_id: authorStore.currentAuthorId,
    context: limitTailText(stripHtml(localContent.value)),
    prompt: userPrompt,
    target_words: chapter.target_words || undefined,
    generation_mode: mode,
    web_search_enabled: canWebSearch.value ? webSearchThisTime.value : undefined,
  };
  lastGenerateParams = { ...params, web_search_enabled: params.web_search_enabled };
  try {
    const ok = await runStreamOnce(params);
    if (ok) {
      streamingText.value = sanitizeGeneratedText(streamingText.value);
      aiProgress.setDetail(`生成完毕，当前约 ${generatedWordCount.value} 字，请确认后并入正文。`);
      aiProgress.finishSuccess(550);
      showConfirmBar.value = true;
    }
  } catch (e) {
    aiProgress.setDetail(String(e));
    aiProgress.finishError();
    ElMessage.error(String(e));
    streamingText.value = "";
  } finally {
    generating.value = false;
  }
}

function stopGeneration() {
  stoppedByUser = true;
  abortController?.abort();
  generating.value = false;
  streamingText.value = sanitizeGeneratedText(streamingText.value);
  if (streamingText.value.trim()) showConfirmBar.value = true;
  aiProgress.setDetail("已停止生成。");
  aiProgress.finishError();
}

async function handleSend() {
  const userPrompt = prompt.value.trim();
  if (!userPrompt) return;
  prompt.value = "";
  await startGeneration(userPrompt, "续写发送");
}

async function generateFromSummary() {
  const chapter = store.currentChapter;
  if (!chapter) return;
  if (!chapter.summary?.trim()) {
    ElMessage.warning("请先在章节里填写本章梗概");
    return;
  }
  const promptText = [
    "请根据本章梗概生成本章正文。",
    "可以参考小说简介和全书大纲来保持主线方向、人物动机与伏笔一致。",
    "只写当前章节，不要写全书主线的后续章节，不要把整本书的事件一次写完。",
    "如果全书大纲包含后续章节事件，只能作为方向参考，不得直接展开或提前发生。",
    "要求：只输出小说正文，不要解释；场景推进清楚，人物行动具体，避免空泛总结。",
    "禁止输出括号里的写作说明、下一章描写计划、作者备注、提纲说明。",
    chapter.target_words ? `目标长度：约 ${chapter.target_words} 字。` : "长度：按梗概完整展开，先生成一个自然章节段落。",
  ].join("\n");
  await startGeneration(promptText, "按梗概生成正文", "chapter_from_summary");
}

function acceptGenerated() {
  const appended = sanitizeGeneratedText(streamingText.value);
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
  stoppedByUser = false;
  runStreamOnce(params).then((ok) => {
    if (ok) {
      streamingText.value = sanitizeGeneratedText(streamingText.value);
      aiProgress.setDetail(`生成完毕，当前约 ${generatedWordCount.value} 字，请确认后接受。`);
      aiProgress.finishSuccess(500);
      showConfirmBar.value = true;
    }
    generating.value = false;
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
.chapter-toolbar {
  flex-shrink: 0;
  margin: 10px 16px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.word-stats {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.outline-generate-btn {
  flex-shrink: 0;
}
.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  min-height: 0;
  overflow: hidden;
}
.editor-area-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.editor-inner {
  flex: 1;
  min-height: 0;
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
  padding: 0 12px 12px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.stream-head {
  position: sticky;
  top: 0;
  z-index: 2;
  margin: 0 -12px 10px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 14px 14px 0 0;
}
.stream-label,
.stream-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.stream-label {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.stream-text {
  max-height: min(42vh, 420px);
  overflow-y: auto;
  padding-right: 4px;
  white-space: pre-wrap;
  line-height: 1.7;
  font-size: 14px;
}
.confirm-bar {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.send-btn {
  min-width: 88px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

@media (max-width: 760px) {
  .chapter-toolbar,
  .stream-head,
  .prompt-inner {
    align-items: stretch;
    flex-direction: column;
  }
  .outline-generate-btn,
  .send-btn {
    width: 100%;
  }
}
</style>
