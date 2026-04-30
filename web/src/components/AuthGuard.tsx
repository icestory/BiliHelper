import { Navigate } from "react-router-dom";
import { getAccessToken } from "../api/client";
import NavBar from "./NavBar";

interface Props {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: Props) {
  const token = getAccessToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return (
    <>
      <NavBar />
      {children}
    </>
  );
}
