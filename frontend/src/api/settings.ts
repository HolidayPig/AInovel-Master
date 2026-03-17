import { api } from "./client";
import type { Settings } from "@/types";

export function listSettings() {
  return api.get<Settings[]>("/settings");
}

export function createSettings(data: {
  provider: string;
  api_key_encrypted?: string;
  model_name?: string;
  proxy_url?: string | null;
  web_search_enabled?: boolean;
  extra_config_json?: string;
}) {
  return api.post<Settings>("/settings", data);
}

export function getSettings(id: number) {
  return api.get<Settings>(`/settings/${id}`);
}

export function updateSettings(
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
  return api.patch<Settings>(`/settings/${id}`, data);
}

export function deleteSettings(id: number) {
  return api.delete(`/settings/${id}`);
}
