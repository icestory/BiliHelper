import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { loadTokens } from "./api/client";
import "./index.css";

// 恢复登录态 — 避免页面刷新后丢失 token
loadTokens();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
