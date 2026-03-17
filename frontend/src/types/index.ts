export interface Novel {
  id: number;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Chapter {
  id: number;
  novel_id: number;
  title: string;
  content: string;
  summary: string | null;
  target_words: number | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export type CardType = "character" | "worldview" | "setting" | "plot" | "custom";

export interface Card {
  id: number;
  novel_id: number;
  card_type: CardType;
  name: string;
  content_json: string;
  auto_update: boolean;
  created_at: string;
  updated_at: string;
}

export interface Settings {
  id: number;
  provider: string;
  model_name: string;
  proxy_url: string | null;
  web_search_enabled: boolean;
  extra_config_json: string;
  created_at: string;
  updated_at: string;
}

export interface Author {
  id: number;
  name: string;
  style: string;
  format_rules: string;
  extra_json: string;
  created_at: string;
  updated_at: string;
}
