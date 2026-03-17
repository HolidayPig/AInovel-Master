import { api } from "./client";
import type { Author } from "@/types";

export function listAuthors() {
  return api.get<Author[]>("/authors");
}

export function createAuthor(data: {
  name: string;
  style?: string;
  format_rules?: string;
  extra_json?: string;
}) {
  return api.post<Author>("/authors", data);
}

export function getAuthor(id: number) {
  return api.get<Author>(`/authors/${id}`);
}

export function updateAuthor(
  id: number,
  data: { name?: string; style?: string; format_rules?: string; extra_json?: string }
) {
  return api.patch<Author>(`/authors/${id}`, data);
}

export function deleteAuthor(id: number) {
  return api.delete(`/authors/${id}`);
}
