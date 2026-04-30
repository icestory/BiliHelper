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
