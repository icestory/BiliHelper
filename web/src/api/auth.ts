import { apiFetch } from "./client";

export function login(username: string, password: string) {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function register(username: string, password: string, email?: string) {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password, email: email || null }),
  });
}

export function getMe() {
  return apiFetch("/auth/me");
}
