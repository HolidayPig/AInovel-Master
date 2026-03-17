import { defineStore } from "pinia";
import { ref } from "vue";
import type { Novel, Chapter, Card } from "@/types";
import * as novelApi from "@/api/novels";
import * as chapterApi from "@/api/chapters";
import * as cardApi from "@/api/cards";

export const useNovelStore = defineStore("novel", () => {
  const novels = ref<Novel[]>([]);
  const currentNovel = ref<Novel | null>(null);
  const chapters = ref<Chapter[]>([]);
  const currentChapter = ref<Chapter | null>(null);
  const cards = ref<Card[]>([]);

  async function fetchNovels() {
    const res = await novelApi.listNovels();
    novels.value = res.data;
    return res.data;
  }

  async function createNovel(data?: string | { title?: string; description?: string }) {
    const payload =
      typeof data === "object"
        ? { title: data.title || "未命名小说", description: data.description }
        : { title: data || "未命名小说" };
    const res = await novelApi.createNovel(payload);
    novels.value.unshift(res.data);
    return res.data;
  }

  async function selectNovel(novel: Novel | null) {
    currentNovel.value = novel;
    currentChapter.value = null;
    if (novel) {
      const res = await chapterApi.listChapters(novel.id);
      chapters.value = res.data;
      const cardRes = await cardApi.listCards(novel.id);
      cards.value = cardRes.data;
    } else {
      chapters.value = [];
      cards.value = [];
    }
  }

  async function updateNovel(id: number, data: { title?: string; description?: string }) {
    const res = await novelApi.updateNovel(id, data);
    const idx = novels.value.findIndex((n) => n.id === id);
    if (idx >= 0) novels.value[idx] = res.data;
    if (currentNovel.value?.id === id) currentNovel.value = res.data;
    return res.data;
  }

  async function deleteNovel(id: number) {
    await novelApi.deleteNovel(id);
    novels.value = novels.value.filter((n) => n.id !== id);
    if (currentNovel.value?.id === id) {
      currentNovel.value = null;
      chapters.value = [];
      currentChapter.value = null;
      cards.value = [];
    }
  }

  async function fetchChapters() {
    if (!currentNovel.value) return;
    const res = await chapterApi.listChapters(currentNovel.value.id);
    chapters.value = res.data;
    return res.data;
  }

  async function createChapter(
    data?: string | { title?: string; summary?: string; target_words?: number }
  ) {
    if (!currentNovel.value) return null;
    const sortOrder = chapters.value.length;
    const payload =
      typeof data === "object"
        ? {
            novel_id: currentNovel.value.id,
            title: data.title || "未命名章节",
            summary: data.summary || null,
            target_words: data.target_words ?? null,
            sort_order: sortOrder,
          }
        : {
            novel_id: currentNovel.value.id,
            title: data || "未命名章节",
            sort_order: sortOrder,
          };
    const res = await chapterApi.createChapter(payload);
    chapters.value.push(res.data);
    return res.data;
  }

  async function selectChapter(chapter: Chapter | null) {
    currentChapter.value = chapter;
    return chapter;
  }

  async function updateChapter(
    id: number,
    data: { title?: string; content?: string; summary?: string | null; target_words?: number | null; sort_order?: number }
  ) {
    const res = await chapterApi.updateChapter(id, data);
    const idx = chapters.value.findIndex((c) => c.id === id);
    if (idx >= 0) chapters.value[idx] = res.data;
    if (currentChapter.value?.id === id) currentChapter.value = res.data;
    return res.data;
  }

  async function deleteChapter(id: number) {
    await chapterApi.deleteChapter(id);
    chapters.value = chapters.value.filter((c) => c.id !== id);
    if (currentChapter.value?.id === id) currentChapter.value = null;
  }

  async function fetchCards() {
    if (!currentNovel.value) return;
    const res = await cardApi.listCards(currentNovel.value.id);
    cards.value = res.data;
    return res.data;
  }

  async function createCard(data: {
    novel_id: number;
    card_type: string;
    name?: string;
    content_json?: string;
    auto_update?: boolean;
  }) {
    const res = await cardApi.createCard(data);
    cards.value.push(res.data);
    return res.data;
  }

  async function updateCard(
    id: number,
    data: { card_type?: string; name?: string; content_json?: string; auto_update?: boolean }
  ) {
    const res = await cardApi.updateCard(id, data);
    const idx = cards.value.findIndex((c) => c.id === id);
    if (idx >= 0) cards.value[idx] = res.data;
    return res.data;
  }

  async function deleteCard(id: number) {
    await cardApi.deleteCard(id);
    cards.value = cards.value.filter((c) => c.id !== id);
  }

  return {
    novels,
    currentNovel,
    chapters,
    currentChapter,
    cards,
    fetchNovels,
    createNovel,
    selectNovel,
    updateNovel,
    deleteNovel,
    fetchChapters,
    createChapter,
    selectChapter,
    updateChapter,
    deleteChapter,
    fetchCards,
    createCard,
    updateCard,
    deleteCard,
  };
});
