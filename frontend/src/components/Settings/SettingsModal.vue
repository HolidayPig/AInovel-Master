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
      <el-form-item label="联网工具">
        <el-switch
          v-model="form.supports_web_search"
          inline-prompt
          active-text="支持"
          inactive-text="不支持"
        />
        <span class="form-hint">仅表示“该模型/接口支持联网工具”，实际是否联网由发送时开关决定</span>
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
  base_url: "",
  supports_web_search: false,
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
  const cur = selectedId.value != null ? settingsStore.list.find((s) => s.id === selectedId.value!) ?? null : null;
  if (cur) {
    form.value = {
      provider: cur.provider,
      api_key_encrypted: "",
      model_name: cur.model_name || "",
      proxy_url: cur.proxy_url ?? "",
      base_url: "",
      supports_web_search: false,
    };
    if (cur.extra_config_json) {
      try {
        const o = JSON.parse(cur.extra_config_json);
        form.value.base_url = o.base_url || "";
        form.value.supports_web_search = !!(o.supports_web_search ?? o.web_search_supported ?? o.enable_web_search);
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
      if (form.value.base_url) extra.base_url = form.value.base_url;
      else delete extra.base_url;
    } else {
      // non-custom: don't carry base_url accidentally
      delete extra.base_url;
    }
    extra.supports_web_search = !!form.value.supports_web_search;
    payload.extra_config_json = JSON.stringify(extra);
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
