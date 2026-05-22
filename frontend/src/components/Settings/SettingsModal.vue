<template>
  <el-dialog
    v-model="dialogVisible"
    title="API 与模型设置"
    width="640px"
    destroy-on-close
    append-to-body
    align-center
    @open="onOpen"
    @close="emit('update:visible', false)"
  >
    <el-form v-if="selectedId != null" :model="form" label-position="top" class="settings-form">
      <section class="settings-section">
        <div class="section-head">
          <div>
            <div class="section-title">当前配置</div>
            <div class="section-subtitle">选择后立即作为续写、卡片更新和大纲生成的默认配置</div>
          </div>
          <el-tag type="success" effect="plain">正在使用</el-tag>
        </div>
        <div class="config-row">
          <el-select v-model="selectedId" placeholder="选择配置" class="config-select">
            <el-option
              v-for="s in settingsStore.list"
              :key="s.id"
              :label="settingLabel(s)"
              :value="s.id"
            />
          </el-select>
          <el-button :icon="Plus" @click="handleCreateConfig">新建</el-button>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-title">服务商</div>
        <el-radio-group v-model="form.provider" class="provider-group" @change="handleProviderChange">
          <el-radio-button
            v-for="p in providerOptions"
            :key="p.value"
            :label="p.value"
          >
            {{ p.label }}
          </el-radio-button>
        </el-radio-group>
        <el-alert :title="providerHint" type="info" :closable="false" show-icon class="provider-hint" />
      </section>

      <section class="settings-section">
        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key_encrypted"
            type="password"
            placeholder="已保存的 Key 不会显示；留空表示不修改"
            show-password
            autocomplete="off"
          />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="form.model_name" :placeholder="modelPlaceholder" />
          <div class="preset-row">
            <el-button
              v-for="m in modelPresets"
              :key="m"
              size="small"
              text
              @click="form.model_name = m"
            >
              {{ m }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item v-if="form.provider === 'custom'" label="自定义 Base URL">
          <el-input
            v-model="form.base_url"
            placeholder="https://your-api.com/v1"
          />
          <div class="form-hint">仅自定义 OpenAI 兼容接口需要填写，末尾是否带 / 均可。</div>
        </el-form-item>
      </section>

      <section class="settings-section two-column">
        <el-form-item label="代理地址">
          <el-input
            v-model="form.proxy_url"
            placeholder="http://127.0.0.1:7890"
          />
          <div class="form-hint">使用 Clash 等代理时填写；必须包含 http://、https:// 或 socks5://。</div>
        </el-form-item>
        <el-form-item label="联网能力">
          <div class="switch-row">
            <el-switch
              v-model="form.supports_web_search"
              :disabled="webSearchLocked"
              inline-prompt
              active-text="支持"
              inactive-text="不支持"
            />
            <span class="form-hint">{{ webSearchHint }}</span>
          </div>
        </el-form-item>
      </section>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="Check" :loading="saving" @click="handleSave">保存并使用</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useSettingsStore } from "@/stores/settings";
import { ElMessage } from "element-plus";
import { Check, Plus } from "@element-plus/icons-vue";
import type { Settings } from "@/types";

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{ "update:visible": [v: boolean] }>();

const settingsStore = useSettingsStore();
const dialogVisible = computed({
  get: () => props.visible,
  set: (v) => emit("update:visible", v),
});

const selectedId = ref<number | null>(null);
const form = ref({
  provider: "openai",
  api_key_encrypted: "",
  model_name: "gpt-4o-mini",
  proxy_url: "" as string | null,
  base_url: "",
  supports_web_search: false,
});
const saving = ref(false);

const providerOptions = [
  { label: "OpenAI", value: "openai" },
  { label: "xAI", value: "xai" },
  { label: "Anthropic", value: "anthropic" },
  { label: "自定义", value: "custom" },
];

const presetByProvider: Record<string, string[]> = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
  grok: ["grok-4.3", "grok-4-latest", "grok-3"],
  xai: ["grok-4.3", "grok-4-latest", "grok-3"],
  anthropic: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
  custom: ["gpt-4o-mini", "deepseek-chat", "glm-4-plus"],
};

function providerLabel(p: string) {
  const map: Record<string, string> = {
    openai: "OpenAI",
    grok: "xAI",
    xai: "xAI",
    anthropic: "Anthropic",
    custom: "自定义",
  };
  return map[p] || p;
}

function settingLabel(s: Settings) {
  return `${providerLabel(s.provider)} - ${s.model_name || "未选模型"}`;
}

const modelPresets = computed(() => presetByProvider[form.value.provider] || presetByProvider.openai);
const allPresetModels = Object.values(presetByProvider).flat();
const modelPlaceholder = computed(() => {
  const first = modelPresets.value?.[0] || "gpt-4o-mini";
  return `例如 ${first}`;
});
const webSearchLocked = computed(() => form.value.provider === "grok" || form.value.provider === "xai");
const providerHint = computed(() => {
  if (form.value.provider === "custom") return "用于兼容 OpenAI Chat Completions 的第三方服务，请同时填写 Base URL。";
  if (form.value.provider === "anthropic") return "Anthropic 使用 Claude Messages API，模型名需填写 Claude 官方模型名。";
  if (form.value.provider === "grok" || form.value.provider === "xai") return "xAI/Grok 默认支持联网工具，续写时仍可按次选择是否联网。";
  return "OpenAI 官方接口通常不需要 Base URL；如需中转，请选择“自定义”。";
});
const webSearchHint = computed(() => {
  if (webSearchLocked.value) return "xAI/Grok 默认支持；实际联网仍由发送时开关决定。";
  return "仅声明接口能力；不支持时会隐藏续写联网开关并阻止卡片联网查询。";
});

function syncFormFromSettings() {
  const cur = selectedId.value != null ? settingsStore.list.find((s) => s.id === selectedId.value!) ?? null : null;
  if (cur) {
    form.value = {
      provider: cur.provider,
      api_key_encrypted: "",
      model_name: cur.model_name || "",
      proxy_url: cur.proxy_url ?? "",
      base_url: "",
      supports_web_search: cur.provider === "grok" || cur.provider === "xai",
    };
    if (cur.extra_config_json) {
      try {
        const o = JSON.parse(cur.extra_config_json);
        form.value.base_url = o.base_url || "";
        form.value.supports_web_search =
          cur.provider === "grok" ||
          cur.provider === "xai" ||
          !!(o.supports_web_search ?? o.web_search_supported ?? o.enable_web_search);
      } catch {}
    }
  }
}

async function onOpen() {
  await settingsStore.fetchSettings();
  if (!settingsStore.list.length) {
    await settingsStore.createDefault();
  }
  selectedId.value = settingsStore.currentId ?? settingsStore.list[0]?.id ?? null;
  syncFormFromSettings();
}

watch(selectedId, (id) => {
  settingsStore.setCurrent(id);
  syncFormFromSettings();
});

function handleProviderChange() {
  if ((!form.value.model_name || allPresetModels.includes(form.value.model_name)) && modelPresets.value?.[0]) {
    form.value.model_name = modelPresets.value[0]!;
  }
  if (webSearchLocked.value) {
    form.value.supports_web_search = true;
  } else {
    form.value.supports_web_search = false;
  }
  if (form.value.provider !== "custom") {
    form.value.base_url = "";
  }
}

async function handleCreateConfig() {
  const created = await settingsStore.createDefault();
  selectedId.value = created.id;
  syncFormFromSettings();
}

function validateForm() {
  const proxy = (form.value.proxy_url || "").trim();
  if (proxy && !/^(https?|socks5):\/\//i.test(proxy)) {
    ElMessage.warning("代理地址需要包含协议，例如 http://127.0.0.1:7890");
    return false;
  }
  if (form.value.provider === "custom") {
    const baseUrl = form.value.base_url.trim();
    if (!baseUrl) {
      ElMessage.warning("自定义服务商需要填写 Base URL");
      return false;
    }
    if (!/^https?:\/\//i.test(baseUrl)) {
      ElMessage.warning("Base URL 需要以 http:// 或 https:// 开头");
      return false;
    }
  }
  return true;
}

async function handleSave() {
  if (selectedId.value == null) return;
  if (!validateForm()) return;
  saving.value = true;
  try {
    const payload: Parameters<typeof settingsStore.updateSettings>[1] = {
      provider: form.value.provider,
      model_name: form.value.model_name,
      proxy_url: form.value.proxy_url || null,
    };
    if (form.value.api_key_encrypted) payload.api_key_encrypted = form.value.api_key_encrypted;
    // extra_config_json: keep existing keys and merge user edits
    let extra: Record<string, unknown> = {};
    const cur = selectedId.value != null ? settingsStore.list.find((s) => s.id === selectedId.value!) ?? null : null;
    if (cur?.extra_config_json) {
      try {
        const o = JSON.parse(cur.extra_config_json);
        if (o && typeof o === "object") extra = { ...(o as Record<string, unknown>) };
      } catch {}
    }
    if (form.value.provider === "custom") {
      if (form.value.base_url.trim()) extra.base_url = form.value.base_url.trim();
      else delete extra.base_url;
    } else {
      // non-custom: don't carry base_url accidentally
      delete extra.base_url;
    }
    extra.supports_web_search = webSearchLocked.value || !!form.value.supports_web_search;
    payload.extra_config_json = JSON.stringify(extra);
    await settingsStore.updateSettings(selectedId.value, payload);
    settingsStore.setCurrent(selectedId.value);
    ElMessage.success("已保存并设为当前配置");
    dialogVisible.value = false;
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.settings-section {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px 16px;
  background: var(--el-fill-color-blank);
}

.section-head,
.config-row,
.switch-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-head {
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.section-subtitle,
.form-hint {
  font-size: 12px;
  line-height: 18px;
  color: var(--el-text-color-secondary);
}

.config-select {
  flex: 1;
  min-width: 0;
}

.provider-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.provider-group :deep(.el-radio-button__inner) {
  border-left: 1px solid var(--el-border-color);
  border-radius: 6px;
  min-width: 104px;
}

.provider-group :deep(.el-radio-button:first-child .el-radio-button__inner),
.provider-group :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 6px;
}

.provider-hint {
  margin-top: 12px;
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.two-column {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.8fr);
  gap: 16px;
}

.two-column :deep(.el-form-item) {
  margin-bottom: 0;
}

.switch-row {
  min-height: 32px;
  align-items: flex-start;
  flex-direction: column;
}

@media (max-width: 720px) {
  .config-row,
  .two-column {
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }

  .provider-group :deep(.el-radio-button__inner) {
    min-width: 88px;
  }
}
</style>
