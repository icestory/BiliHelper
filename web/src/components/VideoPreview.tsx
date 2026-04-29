import type { VideoParseResponse } from "../types";

interface Props {
  data: VideoParseResponse;
  onStartAnalysis?: (partIds: number[]) => void;
}

export default function VideoPreview({ data, onStartAnalysis }: Props) {
  const { video, parts, already_analyzed } = data;

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

      {parts.length > 0 && (
        <div>
          <h3>分 P 列表</h3>
          <ul>
            {parts.map((p) => (
              <li key={p.page_no}>
                P{p.page_no} {p.title}
                {p.duration && <> ({Math.floor(p.duration / 60)} 分钟)</>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {onStartAnalysis && (
        <button onClick={() => onStartAnalysis(parts.filter(p => p.id != null).map(p => p.id!))}>
          开始分析
        </button>
      )}
    </div>
  );
}
