import { api } from "./client";
import type { ConsistencyCheck, Novel, NovelStats, WorkspacePayload } from "@/types";

export function listNovels() {
  return api.get<Novel[]>("/novels");
}

export function createNovel(data: { title?: string; description?: string; outline?: string }) {
  return api.post<Novel>("/novels", data);
}

export function getNovel(id: number) {
  return api.get<Novel>(`/novels/${id}`);
}

export function updateNovel(id: number, data: { title?: string; description?: string; outline?: string }) {
  return api.patch<Novel>(`/novels/${id}`, data);
}

export function deleteNovel(id: number) {
  return api.delete(`/novels/${id}`);
}

export function getNovelStats(id: number) {
  return api.get<NovelStats>(`/novels/${id}/stats`);
}

export function getWorkspace(id: number) {
  return api.get<WorkspacePayload>(`/novels/${id}/workspace`);
}

export function runConsistencyCheck(
  id: number,
  data: { settings_id: number; scope: "chapter" | "recent" | "all"; chapter_id?: number | null }
) {
  return api.post<ConsistencyCheck[]>(`/novels/${id}/consistency-check`, data, { timeout: 660000 });
}
