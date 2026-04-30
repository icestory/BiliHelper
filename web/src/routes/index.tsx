import { createBrowserRouter, Navigate } from "react-router-dom";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import VideoNewPage from "../pages/VideoNewPage";
import HistoryPage from "../pages/HistoryPage";
import VideoDetailPage from "../pages/VideoDetailPage";
import TaskProgressPage from "../pages/TaskProgressPage";
import PartAnalysisPage from "../pages/PartAnalysisPage";
import QAPage from "../pages/QAPage";
import SettingsPage from "../pages/SettingsPage";
import AuthGuard from "../components/AuthGuard";

const auth = (el: React.ReactNode) => <AuthGuard>{el}</AuthGuard>;

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  { path: "/settings", element: auth(<SettingsPage />) },
  { path: "/videos/new", element: auth(<VideoNewPage />) },
  { path: "/history", element: auth(<HistoryPage />) },
  { path: "/videos/:videoId", element: auth(<VideoDetailPage />) },
  { path: "/videos/:videoId/parts/:partId", element: auth(<PartAnalysisPage />) },
  { path: "/videos/:videoId/qa", element: auth(<QAPage />) },
  { path: "/tasks/:taskId", element: auth(<TaskProgressPage />) },
  { path: "/", element: <Navigate to="/login" replace /> },
  { path: "*", element: <Navigate to="/login" replace /> },
]);
