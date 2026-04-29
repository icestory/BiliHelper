import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory, deleteVideoHistory } from "../api/videos";
import type { VideoHistoryItem } from "../types";

export default function HistoryPage() {
  const [items, setItems] = useState<VideoHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const fetchHistory = async () => {
    setLoading(true);
    setError("");
    try {
      const params: Record<string, string | number> = { page };
      if (q.trim()) params.q = q.trim();
      const res = await getHistory(params);
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "加载失败");
        return;
      }
      const data = await res.json();
      setItems(data.items || []);
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page]);

  const handleDelete = async (videoId: number) => {
    if (!confirm("确定删除该视频的分析记录？")) return;
    const res = await deleteVideoHistory(videoId);
    if (res.ok) {
      setItems(items.filter((i) => i.id !== videoId));
    }
  };

  return (
    <div>
      <h1>分析历史</h1>
      <div style={{ marginBottom: "1rem" }}>
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜索视频..."
          onKeyDown={(e) => e.key === "Enter" && fetchHistory()}
        />
        <button onClick={fetchHistory}>搜索</button>
      </div>

      {loading && <p>加载中...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && items.length === 0 && <p>暂无分析记录</p>}

      <div>
        {items.map((video) => (
          <div key={video.id} style={{ display: "flex", gap: "1rem", marginBottom: "1rem", padding: "0.5rem", border: "1px solid #ddd", borderRadius: 8 }}>
            {video.cover_url && <img src={video.cover_url} alt="" style={{ width: 120, borderRadius: 4 }} />}
            <div style={{ flex: 1 }}>
              <Link to={`/videos/${video.id}`} style={{ fontWeight: "bold", fontSize: "1.1rem" }}>
                {video.title}
              </Link>
              <p>UP 主：{video.owner_name || "未知"} | {video.part_count} P</p>
              <p style={{ color: "#999", fontSize: "0.85rem" }}>{video.created_at}</p>
            </div>
            <button onClick={() => handleDelete(video.id)} style={{ alignSelf: "flex-start", color: "red" }}>
              删除
            </button>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "1rem" }}>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
        <span style={{ margin: "0 0.5rem" }}>第 {page} 页</span>
        <button onClick={() => setPage(page + 1)}>下一页</button>
      </div>
    </div>
  );
}
