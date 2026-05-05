import { Link, useNavigate } from "react-router-dom";
import { logout } from "../api/auth";
import { clearTokens, getRefreshToken } from "../api/client";

export default function NavBar() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await logout(refreshToken);
      } catch {
        // 本地退出优先，服务端撤销失败不阻塞用户离开当前会话。
      }
    }
    clearTokens();
    navigate("/login");
  };

  return (
    <nav style={{
      display: "flex", gap: "1rem", alignItems: "center",
      padding: "0.5rem 1rem", background: "#1a1a2e", color: "white",
      marginBottom: "1rem",
    }}>
      <Link to="/videos/new" style={{ color: "white", textDecoration: "none", fontWeight: "bold" }}>
        BiliHelper
      </Link>
      <Link to="/videos/new" style={{ color: "#ccc", textDecoration: "none" }}>
        分析视频
      </Link>
      <Link to="/history" style={{ color: "#ccc", textDecoration: "none" }}>
        历史记录
      </Link>
      <Link to="/settings" style={{ color: "#ccc", textDecoration: "none" }}>
        设置
      </Link>
      <span style={{ flex: 1 }} />
      <button onClick={handleLogout} style={{ background: "none", border: "1px solid #666", color: "#ccc", cursor: "pointer", padding: "0.25rem 0.5rem" }}>
        退出
      </button>
    </nav>
  );
}
