import { apiFetch } from "./client";

export function parseVideo(url: string) {
  return apiFetch("/videos/parse", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function getHistory(params?: {
  page?: number;
  page_size?: number;
  q?: string;
  owner?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.q) searchParams.set("q", params.q);
  if (params?.owner) searchParams.set("owner", params.owner);
  const qs = searchParams.toString();
  return apiFetch(`/videos/history${qs ? `?${qs}` : ""}`);
}

export function getVideoDetail(videoId: number) {
  return apiFetch(`/videos/${videoId}`);
}

export function deleteVideoHistory(videoId: number) {
  return apiFetch(`/videos/${videoId}/history`, { method: "DELETE" });
}
