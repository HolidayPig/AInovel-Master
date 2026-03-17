import type { CardType } from "@/types";

export const CARD_TYPE_LABELS: Record<CardType, string> = {
  character: "角色",
  worldview: "世界观",
  setting: "设定",
  plot: "剧情线",
  custom: "自定义",
};

export const CARD_TYPE_FIELDS: Record<CardType, { key: string; label: string }[]> = {
  character: [{ key: "text", label: "详细描述" }],
  worldview: [{ key: "text", label: "详细描述" }],
  setting: [{ key: "text", label: "详细描述" }],
  plot: [{ key: "text", label: "详细描述" }],
  custom: [{ key: "text", label: "内容" }],
};

export function defaultContentJson(cardType: CardType): string {
  const fields = CARD_TYPE_FIELDS[cardType];
  const o: Record<string, string> = {};
  for (const f of fields) o[f.key] = "";
  return JSON.stringify(o, null, 2);
}
