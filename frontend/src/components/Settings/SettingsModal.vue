<template>
  <el-dialog
    v-model="dialogVisible"
    title="API 与模型设置"
    width="520px"
    destroy-on-close
    append-to-body
    align-center
    @open="onOpen"
    @close="emit('update:visible', false)"
  >
    <el-form v-if="selectedId != null" :model="form" label-width="100px" label-position="left">
      <el-form-item label="配置">
        <el-select v-model="selectedId" placeholder="选择配置" style="width: 100%">
          <el-option
            v-for="s in settingsStore.list"
            :key="s.id"
            :label="`${providerLabel(s.provider)} - ${s.model_name || '未选模型'}`"
            :value="s.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="服务商">
        <el-select v-model="form.provider" placeholder="选择服务商" style="width: 100%">
          <el-option label="OpenAI (GPT)" value="openai" />
          <el-option label="xAI (Grok)" value="grok" />
          <el-option label="Anthropic (Claude)" value="anthropic" />
          <el-option label="自定义 (OpenAI 兼容)" value="custom" />
        </el-select>
      </el-form-item>
      <el-form-item label="API Key">
        <el-input
          v-model="form.api_key_encrypted"
          type="password"
          placeholder="留空则不修改已保存的 Key"
          show-password
          autocomplete="off"
        />
      </el-form-item>
      <el-form-item label="模型">
        <el-input v-model="form.model_name" placeholder="如 gpt-4o、grok-2、claude-3-5-sonnet" />
      </el-form-item>
      <el-form-item label="代理地址">
        <el-input
          v-model="form.proxy_url"
          placeholder="如 http://127.0.0.1:7890（Clash 等）"
        />
      </el-form-item>
      <el-form-item v-if="form.provider === 'grok' || form.provider === 'xai'" label="联网搜索">
        <el-switch v-model="form.web_search_enabled" />
        <span class="form-hint">开启后 Grok 可联网搜索</span>
      </el-form-item>
      <el-form-item v-if="form.provider === 'custom'" label="自定义 Base URL">
        <el-input
          v-model="form.base_url"
          placeholder="https://your-api.com/v1"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useSettingsStore } from "@/stores/settings";
import { ElMessage } from "element-plus";

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
  web_search_enabled: false,
  base_url: "",
});
const saving = ref(false);

function providerLabel(p: string) {
  const map: Record<string, string> = {
    openai: "OpenAI",
    grok: "Grok",
    xai: "xAI",
    anthropic: "Anthropic",
    custom: "自定义",
  };
  return map[p] || p;
}

function syncFormFromSettings() {
  const cur = selectedId.value != null && settingsStore.list.find((s) => s.id === selectedId.value!);
  if (cur) {
    form.value = {
      provider: cur.provider,
      api_key_encrypted: "",
      model_name: cur.model_name || "",
      proxy_url: cur.proxy_url ?? "",
      web_search_enabled: cur.web_search_enabled,
      base_url: "",
    };
    if (cur.extra_config_json) {
      try {
        const o = JSON.parse(cur.extra_config_json);
        form.value.base_url = o.base_url || "";
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

watch(selectedId, () => syncFormFromSettings());

async function handleSave() {
  if (selectedId.value == null) return;
  saving.value = true;
  try {
    const payload: Parameters<typeof settingsStore.updateSettings>[1] = {
      provider: form.value.provider,
      model_name: form.value.model_name,
      proxy_url: form.value.proxy_url || null,
      web_search_enabled: form.value.web_search_enabled,
    };
    if (form.value.api_key_encrypted) payload.api_key_encrypted = form.value.api_key_encrypted;
    if (form.value.provider === "custom" && form.value.base_url) {
      payload.extra_config_json = JSON.stringify({ base_url: form.value.base_url });
    }
    await settingsStore.updateSettings(selectedId.value, payload);
    ElMessage.success("已保存");
    dialogVisible.value = false;
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.form-hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
