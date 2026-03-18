import { api } from "./client";
import type { Chapter } from "@/types";

export function listChapters(novelId: number) {
  return api.get<Chapter[]>("/chapters", { params: { novel_id: novelId } });
}

export function createChapter(data: {
  novel_id: number;
  title?: string;
  content?: string;
  summary?: string | null;
  target_words?: number | null;
  sort_order?: number;
}) {
  return api.post<Chapter>("/chapters", data);
}

export function getChapter(id: number) {
  return api.get<Chapter>(`/chapters/${id}`);
}

export function updateChapter(
  id: number,
  data: { title?: string; content?: string; summary?: string | null; target_words?: number | null; sort_order?: number }
) {
  return api.patch<Chapter>(`/chapters/${id}`, data);
}

export function deleteChapter(id: number) {
  return api.delete(`/chapters/${id}`);
}

export type GenerateChaptersBriefPayload = {
  novel_id: number;
  settings_id: number;
  replace_existing?: boolean;
  synopsis?: string;
  main_line?: string;
  opening?: string;
  early?: string;
  middle?: string;
  late?: string;
  genre?: string;
  tone?: string;
  extra?: string;
  total_chapters?: number;
  target_words_per_chapter?: number;
};

export function generateChaptersFromBrief(data: GenerateChaptersBriefPayload) {
  return api.post<{ outline: string; chapters: Chapter[] }>(
    "/chapters/generate-from-brief",
    data,
    { timeout: 660000 }
  );
}
