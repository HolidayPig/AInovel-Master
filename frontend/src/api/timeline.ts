import { api } from "./client";
import type { TimelineEvent, TimelineEventCandidate } from "@/types";

export function listTimelineEvents(novelId: number) {
  return api.get<TimelineEvent[]>("/timeline-events", { params: { novel_id: novelId } });
}

export function createTimelineEvent(data: {
  novel_id: number;
  chapter_id?: number | null;
  title?: string;
  event_time?: string;
  summary?: string;
  characters?: string;
  sort_order?: number;
}) {
  return api.post<TimelineEvent>("/timeline-events", data);
}

export function updateTimelineEvent(
  id: number,
  data: {
    chapter_id?: number | null;
    title?: string;
    event_time?: string;
    summary?: string;
    characters?: string;
    sort_order?: number;
  }
) {
  return api.patch<TimelineEvent>(`/timeline-events/${id}`, data);
}

export function deleteTimelineEvent(id: number) {
  return api.delete(`/timeline-events/${id}`);
}

export function extractTimelineEvents(data: {
  novel_id: number;
  chapter_id: number;
  settings_id: number;
}) {
  return api.post<TimelineEventCandidate[]>("/timeline-events/extract-from-chapter", data, { timeout: 660000 });
}
