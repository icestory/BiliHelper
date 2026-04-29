import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAnalysisTask } from "../api/analysis";
import type { VideoParseResponse } from "../types";

interface Props {
  data: VideoParseResponse;
}

export default function VideoPreview({ data }: Props) {
  const { video, parts, already_analyzed } = data;
  const [selectedPartIds, setSelectedPartIds] = useState<Set<number>>(
    new Set(parts.filter((p) => p.id != null).map((p) => p.id!))
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const togglePart = (id: number) => {
    const next = new Set(selectedPartIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedPartIds(next);
  };

  const toggleAll = () => {
    const allIds = parts.filter((p) => p.id != null).map((p) => p.id!);
    if (selectedPartIds.size === allIds.length) {
      setSelectedPartIds(new Set());
    } else {
      setSelectedPartIds(new Set(allIds));
    }
  };

  const handleStartAnalysis = async () => {
    if (selectedPartIds.size === 0) return;
    setLoading(true);
    setError("");

    try {
      const res = await createAnalysisTask(video.id!, Array.from(selectedPartIds));
      if (!res.ok) {
        const d = await res.json();
        setError(d.detail || "创建任务失败");
        return;
      }
      const task = await res.json();
      navigate(`/tasks/${task.id}`);
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        {video.cover_url && (
          <img src={video.cover_url} alt={video.title} style={{ width: 160, borderRadius: 8 }} />
        )}
        <div>
          <h2>{video.title}</h2>
          <p>UP 主：{video.owner_name}</p>
          <p>分 P 数：{video.part_count}</p>
          {video.duration && <p>时长：{Math.floor(video.duration / 60)} 分钟</p>}
          {already_analyzed && <p style={{ color: "green" }}>该视频已有分析记录</p>}
        </div>
      </div>

      {video.description && <p style={{ color: "#666" }}>{video.description}</p>}

      {parts.length > 1 && (
        <div>
          <h3>
            选择分析的分 P
            <button onClick={toggleAll} style={{ marginLeft: "1rem", fontSize: "0.85rem" }}>
              {selectedPartIds.size === parts.filter(p => p.id != null).length ? "取消全选" : "全选"}
            </button>
          </h3>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {parts.map((p) => (
              <li key={p.page_no} style={{ padding: "0.25rem 0" }}>
                <label>
                  <input
                    type="checkbox"
                    checked={p.id != null && selectedPartIds.has(p.id)}
                    onChange={() => p.id && togglePart(p.id)}
                    disabled={p.id == null}
                  />
                  P{p.page_no} {p.title}
                  {p.duration && <> ({Math.floor(p.duration / 60)} 分钟)</>}
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p style={{ color: "red" }}>{error}</p>}

      <button onClick={handleStartAnalysis} disabled={loading || selectedPartIds.size === 0}>
        {loading ? "创建任务中..." : "开始分析"}
      </button>
    </div>
  );
}
