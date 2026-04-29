import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { parseVideo } from "../api";
import type { VideoParseResponse } from "../types";

interface Props {
  onParsed?: (data: VideoParseResponse) => void;
}

export default function LinkInput({ onParsed }: Props) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!url.trim()) return;

    setLoading(true);
    try {
      const res = await parseVideo(url.trim());
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "解析失败");
        setLoading(false);
        return;
      }
      const data: VideoParseResponse = await res.json();
      if (onParsed) {
        onParsed(data);
      } else {
        // 默认导航到视频详情
        navigate(`/videos/${data.video.id}`);
      }
    } catch {
      setError("网络错误，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="粘贴 B 站视频链接..."
        style={{ width: "100%", padding: "0.5rem", fontSize: "1rem" }}
        autoFocus
      />
      {error && <p style={{ color: "red" }}>{error}</p>}
      <button type="submit" disabled={loading || !url.trim()}>
        {loading ? "解析中..." : "解析视频"}
      </button>
    </form>
  );
}
