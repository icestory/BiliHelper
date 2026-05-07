import { apiFetch } from "./client";

export function listCredentials() {
  return apiFetch("/llm-configs");
}

export function createCredential(data: {
  provider: string;
  api_key: string;
  api_base_url?: string;
  default_model?: string;
  is_default?: boolean;
}) {
  return apiFetch("/llm-configs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deleteCredential(id: number) {
  return apiFetch(`/llm-configs/${id}`, { method: "DELETE" });
}

export function setDefaultCredential(id: number) {
  return apiFetch(`/llm-configs/${id}/set-default`, { method: "POST" });
}

// ============ B 站 Cookie 凭证 ============

export function listBilibiliCredentials() {
  return apiFetch("/bilibili-credentials");
}

export function createBilibiliCredential(data: {
  sessdata: string;
  bili_jct: string;
  buvid3?: string;
  enabled?: boolean;
}) {
  return apiFetch("/bilibili-credentials", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateBilibiliCredential(id: number, data: {
  sessdata?: string;
  bili_jct?: string;
  buvid3?: string;
  enabled?: boolean;
}) {
  return apiFetch(`/bilibili-credentials/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteBilibiliCredential(id: number) {
  return apiFetch(`/bilibili-credentials/${id}`, { method: "DELETE" });
}

export function enableBilibiliCredential(id: number) {
  return apiFetch(`/bilibili-credentials/${id}/enable`, { method: "POST" });
}
