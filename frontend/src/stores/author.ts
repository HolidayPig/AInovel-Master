import { defineStore } from "pinia";
import { ref } from "vue";
import type { Author } from "@/types";
import * as authorApi from "@/api/authors";

export const useAuthorStore = defineStore("author", () => {
  const authors = ref<Author[]>([]);
  const currentAuthorId = ref<number | null>(null);

  async function fetchAuthors() {
    const res = await authorApi.listAuthors();
    authors.value = res.data;
    return res.data;
  }

  async function createAuthor(data: {
    name: string;
    style?: string;
    format_rules?: string;
  }) {
    const res = await authorApi.createAuthor(data);
    authors.value.unshift(res.data);
    return res.data;
  }

  async function updateAuthor(
    id: number,
    data: { name?: string; style?: string; format_rules?: string }
  ) {
    const res = await authorApi.updateAuthor(id, data);
    const idx = authors.value.findIndex((a) => a.id === id);
    if (idx >= 0) authors.value[idx] = res.data;
    return res.data;
  }

  async function deleteAuthor(id: number) {
    await authorApi.deleteAuthor(id);
    authors.value = authors.value.filter((a) => a.id !== id);
    if (currentAuthorId.value === id) currentAuthorId.value = null;
  }

  function setCurrentAuthor(id: number | null) {
    currentAuthorId.value = id;
  }

  function getCurrentAuthor(): Author | null {
    if (currentAuthorId.value == null) return null;
    return authors.value.find((a) => a.id === currentAuthorId.value!) ?? null;
  }

  return {
    authors,
    currentAuthorId,
    fetchAuthors,
    createAuthor,
    updateAuthor,
    deleteAuthor,
    setCurrentAuthor,
    getCurrentAuthor,
  };
});
