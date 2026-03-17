import { api } from "./client";
import type { Novel } from "@/types";

export function listNovels() {
  return api.get<Novel[]>("/novels");
}

export function createNovel(data: { title?: string; description?: string }) {
  return api.post<Novel>("/novels", data);
}

export function getNovel(id: number) {
  return api.get<Novel>(`/novels/${id}`);
}

export function updateNovel(id: number, data: { title?: string; description?: string }) {
  return api.patch<Novel>(`/novels/${id}`, data);
}

export function deleteNovel(id: number) {
  return api.delete(`/novels/${id}`);
}
