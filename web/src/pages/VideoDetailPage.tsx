import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getVideoDetail } from "../api/videos";
import type { VideoDetailResponse } from "../types";

export default function VideoDetailPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const [video, setVideo] = useState<VideoDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!videoId) return;
    setLoading(true);
    setError("");
    getVideoDetail(Number(videoId))
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          setError(data.detail || "加载失败");
          return;
        }
        const data = await res.json();
        setVideo(data);
      })
      .catch(() => setError("网络错误"))
      .finally(() => setLoading(false));
  }, [videoId]);

  if (loading) return <p>加载中...</p>;
  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!video) return <p>视频不存在</p>;

  return (
    <div>
      <Link to="/history">← 返回历史</Link>
      <div style={{ display: "flex", gap: "1rem", margin: "1rem 0" }}>
        {video.cover_url && (
          <img src={video.cover_url} alt="" style={{ width: 200, borderRadius: 8 }} />
        )}
        <div>
          <h1>{video.title}</h1>
          <p>UP 主：{video.owner_name || "未知"}</p>
          <p>BV 号：{video.bvid}</p>
          {video.duration && <p>时长：{Math.floor(video.duration / 60)} 分钟</p>}
          <p>分 P 数：{video.part_count}</p>
        </div>
      </div>

      {video.description && <p style={{ color: "#666" }}>{video.description}</p>}

      <h2>分 P 列表</h2>
      <ul>
        {video.parts.map((p) => (
          <li key={p.page_no}>
            P{p.page_no} {p.title}
            {p.duration && <> ({Math.floor(p.duration / 60)} 分钟)</>}
          </li>
        ))}
      </ul>
    </div>
  );
}
