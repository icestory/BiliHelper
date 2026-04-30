import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getPartAnalysis } from "../api/analysis";
import ChapterList from "../components/ChapterList";
import TranscriptView from "../components/TranscriptView";
import { STATUS_LABELS, type PartAnalysisDetail } from "../types";

export default function PartAnalysisPage() {
  const { videoId, partId } = useParams<{ videoId: string; partId: string }>();
  const [data, setData] = useState<PartAnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [highlightTime, setHighlightTime] = useState<number | null>(null);

  useEffect(() => {
    if (!partId) return;
    let cancelled = false;
    setError("");
    getPartAnalysis(Number(partId))
      .then(async (res) => {
        if (cancelled) return;
        if (!res.ok) {
          const detail = await res.json();
          setError(detail.detail || "加载失败");
          return;
        }
        setData(await res.json());
      })
      .catch(() => { if (!cancelled) setError("网络错误"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [partId]);

  if (loading) return <p>加载中...</p>;
  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!data) return <p>无数据</p>;

  return (
    <div>
      <Link to={`/videos/${videoId}`}>← 返回视频</Link>

      <p>状态：{STATUS_LABELS[data.status] || data.status}</p>
      {data.transcript_source && <p>字幕来源：{data.transcript_source === "bili_subtitle" ? "B站字幕" : "语音识别"}</p>}

      {data.summary && (
        <div style={{ margin: "1rem 0" }}>
          <h2>摘要</h2>
          <p>{data.summary.summary}</p>
          <h3>详细总结</h3>
          <p>{data.summary.detailed_summary}</p>
          {data.summary.key_points && data.summary.key_points.length > 0 && (
            <>
              <h3>关键要点</h3>
              <ul>
                {data.summary.key_points.map((kp, i) => <li key={i}>{kp}</li>)}
              </ul>
            </>
          )}
        </div>
      )}

      {data.chapters && (
        <ChapterList chapters={data.chapters} onTimeClick={setHighlightTime} />
      )}

      {data.transcript_segments && (
        <TranscriptView segments={data.transcript_segments} highlightTime={highlightTime} />
      )}
    </div>
  );
}
