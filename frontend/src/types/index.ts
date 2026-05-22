export interface Novel {
  id: number;
  title: string;
  description: string | null;
  outline: string;
  created_at: string;
  updated_at: string;
}

export type ChapterStatus = "drafting" | "reviewing" | "done";

export interface Chapter {
  id: number;
  novel_id: number;
  title: string;
  content: string;
  summary: string | null;
  target_words: number | null;
  status: ChapterStatus;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ChapterStats {
  id: number;
  title: string;
  status: ChapterStatus;
  word_count: number;
  target_words: number | null;
  completion_rate: number;
}

export interface NovelStats {
  novel_id: number;
  total_words: number;
  chapter_count: number;
  done_chapter_count: number;
  target_words_total: number;
  completion_rate: number;
  updated_at: string | null;
  chapters: ChapterStats[];
}

export interface TimelineEvent {
  id: number;
  novel_id: number;
  chapter_id: number | null;
  title: string;
  event_time: string;
  summary: string;
  characters: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface TimelineEventCandidate {
  title: string;
  event_time: string;
  summary: string;
  characters: string;
  sort_order: number;
}

export interface ConsistencyCheck {
  id: number;
  novel_id: number;
  chapter_id: number | null;
  check_type: string;
  severity: "low" | "medium" | "high" | string;
  message: string;
  suggestion: string;
  resolved: boolean;
  created_at: string;
}

export interface WorkspaceChapter {
  id: number;
  title: string;
  summary: string | null;
  target_words: number | null;
  status: ChapterStatus;
  sort_order: number;
  word_count: number;
}

export interface WorkspacePayload {
  novel: Novel;
  stats: NovelStats;
  chapters: WorkspaceChapter[];
  recent_timeline_events: TimelineEvent[];
  unresolved_checks: ConsistencyCheck[];
}

export type CardType = "character" | "worldview" | "setting" | "plot" | "custom";

export interface Card {
  id: number;
  novel_id: number;
  card_type: CardType;
  name: string;
  content_json: string;
  auto_update: boolean;
  tags: string;
  importance: number;
  last_referenced_chapter_id: number | null;
  last_referenced_at: string | null;
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
