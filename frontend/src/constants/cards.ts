import type { CardType } from "@/types";

export const CARD_TYPE_LABELS: Record<CardType, string> = {
  character: "角色",
  worldview: "世界观",
  setting: "设定",
  plot: "剧情线",
  custom: "自定义",
};

export const CARD_TYPE_FIELDS: Record<CardType, { key: string; label: string }[]> = {
  character: [
    { key: "name", label: "姓名" },
    { key: "appearance", label: "外貌" },
    { key: "personality", label: "性格" },
    { key: "backstory", label: "背景" },
    { key: "其他", label: "其他" },
  ],
  worldview: [
    { key: "name", label: "名称" },
    { key: "description", label: "描述" },
    { key: "rules", label: "规则/设定" },
  ],
  setting: [
    { key: "name", label: "名称" },
    { key: "description", label: "描述" },
  ],
  plot: [
    { key: "name", label: "名称" },
    { key: "summary", label: "概要" },
  ],
  custom: [{ key: "text", label: "内容" }],
};

export function defaultContentJson(cardType: CardType): string {
  const fields = CARD_TYPE_FIELDS[cardType];
  const o: Record<string, string> = {};
  for (const f of fields) o[f.key] = "";
  return JSON.stringify(o, null, 2);
}
