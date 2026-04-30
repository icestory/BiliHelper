import { Navigate } from "react-router-dom";
import { getAccessToken } from "../api/client";

interface Props {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: Props) {
  const token = getAccessToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
