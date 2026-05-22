import { api } from "./client";
import type { ConsistencyCheck } from "@/types";

export function updateConsistencyCheck(id: number, data: { resolved?: boolean }) {
  return api.patch<ConsistencyCheck>(`/consistency-checks/${id}`, data);
}
