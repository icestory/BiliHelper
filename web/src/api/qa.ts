import { apiFetch } from "./client";

export function listQASessions(videoId: number) {
  return apiFetch(`/videos/${videoId}/qa-sessions`);
}

export function createQASession(videoId: number, title?: string, scope = "video", partIds?: number[]) {
  return apiFetch(`/videos/${videoId}/qa-sessions`, {
    method: "POST",
    body: JSON.stringify({ title, scope, part_ids: partIds }),
  });
}

export function getQAMessages(sessionId: number) {
  return apiFetch(`/qa-sessions/${sessionId}/messages`);
}

export function askQuestion(sessionId: number, question: string) {
  return apiFetch(`/qa-sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
