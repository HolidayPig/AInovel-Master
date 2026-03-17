import { api } from "./client";
import type { Card } from "@/types";

export function listCards(novelId: number) {
  return api.get<Card[]>("/cards", { params: { novel_id: novelId } });
}

export function createCard(data: {
  novel_id: number;
  card_type: string;
  name?: string;
  content_json?: string;
  auto_update?: boolean;
}) {
  return api.post<Card>("/cards", data);
}

export function getCard(id: number) {
  return api.get<Card>(`/cards/${id}`);
}

export function updateCard(
  id: number,
  data: { card_type?: string; name?: string; content_json?: string; auto_update?: boolean }
) {
  return api.patch<Card>(`/cards/${id}`, data);
}

export function deleteCard(id: number) {
  return api.delete(`/cards/${id}`);
}
