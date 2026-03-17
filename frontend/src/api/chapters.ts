import { api } from "./client";
import type { Chapter } from "@/types";

export function listChapters(novelId: number) {
  return api.get<Chapter[]>("/chapters", { params: { novel_id: novelId } });
}

export function createChapter(data: {
  novel_id: number;
  title?: string;
  content?: string;
  sort_order?: number;
}) {
  return api.post<Chapter>("/chapters", data);
}

export function getChapter(id: number) {
  return api.get<Chapter>(`/chapters/${id}`);
}

export function updateChapter(
  id: number,
  data: { title?: string; content?: string; sort_order?: number }
) {
  return api.patch<Chapter>(`/chapters/${id}`, data);
}

export function deleteChapter(id: number) {
  return api.delete(`/chapters/${id}`);
}
