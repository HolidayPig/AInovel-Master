<template>
  <el-dialog
    v-model="visible"
    title="Outline · AI chapters"
    width="600px"
    destroy-on-close
    append-to-body
    align-center
    class="outline-gen-dialog"
    @close="emit('close')"
  >
    <p class="intro">
      填写小说整体规划后，AI 将生成分章标题与每章内容梗概，并批量创建章节。梗概可在选中章节时于中间区查看，或通过右键「编辑」修改。
    </p>
    <el-form :model="form" label-width="108px" label-position="left" class="outline-form">
      <el-form-item label="清空后生成">
        <el-switch v-model="form.replace_existing" active-text="是" inactive-text="否（追加）" />
        <span class="hint">开启将删除本小说现有全部章节再生成</span>
      </el-form-item>
      <el-form-item label="总体梗概" required>
        <el-input
          v-model="form.synopsis"
          type="textarea"
          :rows="3"
          placeholder="一句话到一段话：故事核心、主角目标、世界背景等"
        />
      </el-form-item>
      <el-form-item label="主线">
        <el-input
          v-model="form.main_line"
          type="textarea"
          :rows="2"
          placeholder="贯穿全书的主要矛盾与走向"
        />
      </el-form-item>
      <el-form-item label="开头">
        <el-input
          v-model="form.opening"
          type="textarea"
          :rows="2"
          placeholder="开篇钩子、登场方式、首波冲突"
        />
      </el-form-item>
      <el-form-item label="前期">
        <el-input
          v-model="form.early"
          type="textarea"
          :rows="2"
          placeholder="铺垫、成长、小高潮"
        />
      </el-form-item>
      <el-form-item label="中期">
        <el-input
          v-model="form.middle"
          type="textarea"
          :rows="2"
          placeholder="转折、主线推进、副本或支线"
        />
      </el-form-item>
      <el-form-item label="后期">
        <el-input
          v-model="form.late"
          type="textarea"
          :rows="2"
          placeholder="高潮、收束、结局走向"
        />
      </el-form-item>
      <el-form-item label="类型/题材">
        <el-input v-model="form.genre" placeholder="如：玄幻、悬疑、言情…" />
      </el-form-item>
      <el-form-item label="基调文风">
        <el-input v-model="form.tone" placeholder="如：轻松幽默、压抑写实、热血…" />
      </el-form-item>
      <el-form-item label="其他要求">
        <el-input
          v-model="form.extra"
          type="textarea"
          :rows="2"
          placeholder="禁忌、必须出现的元素、视角人称等"
        />
      </el-form-item>
      <el-form-item label="预计总章数">
        <el-input-number v-model="form.total_chapters" :min="1" :max="120" />
      </el-form-item>
      <el-form-item label="每章目标字数">
        <el-input-number v-model="form.target_words_per_chapter" :min="0" :max="50000" />
        <span class="hint">0 表示由 AI 估计，写入章节后可在编辑中改</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">Generate</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { generateChaptersFromBrief } from "@/api/chapters";
import { ElMessage } from "element-plus";
import { useAiProgressStore } from "@/stores/aiProgress";

const props = defineProps<{
  modelValue: boolean;
  novelId: number;
  settingsId: number | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  close: [];
  done: [payload: { replace_existing: boolean }];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const loading = ref(false);
const aiProgress = useAiProgressStore();
const form = ref({
  replace_existing: false,
  synopsis: "",
  main_line: "",
  opening: "",
  early: "",
  middle: "",
  late: "",
  genre: "",
  tone: "",
  extra: "",
  total_chapters: 20,
  target_words_per_chapter: 3000,
});

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      form.value.replace_existing = false;
    }
  }
);

async function submit() {
  if (!props.novelId) {
    ElMessage.warning("请先选择小说");
    return;
  }
  if (!props.settingsId) {
    ElMessage.warning("请先在右侧「设置」中配置 API 并选择一套模型");
    return;
  }
  const syn = form.value.synopsis.trim();
  if (!syn) {
    ElMessage.warning("请填写总体梗概");
    return;
  }
  loading.value = true;
  const n = form.value.total_chapters;
  aiProgress.start("分章大纲", {
    phase: "thinking",
    detail: `正在请求模型生成约 ${n} 个章节的标题与梗概（可能需数分钟）…`,
  });
  try {
    await generateChaptersFromBrief({
      novel_id: props.novelId,
      settings_id: props.settingsId,
      replace_existing: form.value.replace_existing,
      synopsis: syn,
      main_line: form.value.main_line.trim(),
      opening: form.value.opening.trim(),
      early: form.value.early.trim(),
      middle: form.value.middle.trim(),
      late: form.value.late.trim(),
      genre: form.value.genre.trim(),
      tone: form.value.tone.trim(),
      extra: form.value.extra.trim(),
      total_chapters: form.value.total_chapters,
      target_words_per_chapter: form.value.target_words_per_chapter || 0,
    });
    aiProgress.setDetail("大纲已生成，正在写入章节列表…");
    aiProgress.finishSuccess(700);
    ElMessage.success("已根据大纲创建章节");
    visible.value = false;
    emit("done", { replace_existing: form.value.replace_existing });
  } catch {
    aiProgress.setDetail("生成失败，请减小章数或检查 API");
    aiProgress.finishError();
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.intro {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}
.outline-form {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 4px;
}
.hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
