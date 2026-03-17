import { defineStore } from "pinia";
import { ref } from "vue";
import type { Settings } from "@/types";
import * as settingsApi from "@/api/settings";

export const useSettingsStore = defineStore("settings", () => {
  const list = ref<Settings[]>([]);
  const currentId = ref<number | null>(null);

  async function fetchSettings() {
    const res = await settingsApi.listSettings();
    list.value = res.data;
    if (res.data.length && !currentId.value) currentId.value = res.data[0].id;
    return res.data;
  }

  async function createDefault() {
    const res = await settingsApi.createSettings({
      provider: "openai",
      model_name: "gpt-4o-mini",
    });
    list.value.unshift(res.data);
    currentId.value = res.data.id;
    return res.data;
  }

  async function updateSettings(
    id: number,
    data: {
      provider?: string;
      api_key_encrypted?: string;
      model_name?: string;
      proxy_url?: string | null;
      web_search_enabled?: boolean;
      extra_config_json?: string;
    }
  ) {
    const res = await settingsApi.updateSettings(id, data);
    const idx = list.value.findIndex((s) => s.id === id);
    if (idx >= 0) list.value[idx] = res.data;
    return res.data;
  }

  function current(): Settings | null {
    if (!currentId.value) return null;
    return list.value.find((s) => s.id === currentId.value) ?? null;
  }

  return {
    list,
    currentId,
    fetchSettings,
    createDefault,
    updateSettings,
    current,
  };
});
