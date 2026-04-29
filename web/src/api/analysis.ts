import { apiFetch } from "./client";

export function createAnalysisTask(videoId: number, partIds: number[], forceReanalyze = false) {
  return apiFetch("/analysis-tasks", {
    method: "POST",
    body: JSON.stringify({
      video_id: videoId,
      part_ids: partIds,
      force_reanalyze: forceReanalyze,
    }),
  });
}

export function getAnalysisTask(taskId: number) {
  return apiFetch(`/analysis-tasks/${taskId}`);
}

export function retryAnalysisTask(taskId: number) {
  return apiFetch(`/analysis-tasks/${taskId}/retry`, { method: "POST" });
}

export function reanalyzePart(partId: number, force = false) {
  return apiFetch(`/parts/${partId}/reanalyze?force=${force}`, { method: "POST" });
}

export function getPartAnalysis(partId: number) {
  return apiFetch(`/parts/${partId}/analysis`);
}

export function getVideoSummary(videoId: number) {
  return apiFetch(`/videos/${videoId}/summary`);
}
