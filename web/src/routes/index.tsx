import { createBrowserRouter, Navigate } from "react-router-dom";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import VideoNewPage from "../pages/VideoNewPage";
import HistoryPage from "../pages/HistoryPage";
import VideoDetailPage from "../pages/VideoDetailPage";
import TaskProgressPage from "../pages/TaskProgressPage";
import PartAnalysisPage from "../pages/PartAnalysisPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  { path: "/videos/new", element: <VideoNewPage /> },
  { path: "/history", element: <HistoryPage /> },
  { path: "/videos/:videoId", element: <VideoDetailPage /> },
  { path: "/videos/:videoId/parts/:partId", element: <PartAnalysisPage /> },
  { path: "/tasks/:taskId", element: <TaskProgressPage /> },
  { path: "*", element: <Navigate to="/login" replace /> },
]);
