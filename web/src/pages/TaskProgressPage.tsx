import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { getAnalysisTask, retryAnalysisTask } from "../api/analysis";
import { getVideoSummary } from "../api/analysis";
import TaskProgress from "../components/TaskProgress";
import type { AnalysisTaskResponse, VideoSummaryResponse } from "../types";

export default function TaskProgressPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [task, setTask] = useState<AnalysisTaskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [videoSummary, setVideoSummary] = useState<VideoSummaryResponse | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTask = async () => {
    if (!taskId) return;
    try {
      const res = await getAnalysisTask(Number(taskId));
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "加载失败");
        return;
      }
      const data: AnalysisTaskResponse = await res.json();
      setTask(data);
      if (["completed", "failed", "partial_failed"].includes(data.status)) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        // 任务完成时加载全视频总结
        if (data.status === "completed" || data.status === "partial_failed") {
          getVideoSummary(data.video_id)
            .then(r => r.ok ? r.json() : null)
            .then(s => setVideoSummary(s))
            .catch(() => {});
        }
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTask();
    intervalRef.current = setInterval(fetchTask, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId]);

  const handleRetry = async () => {
    if (!taskId) return;
    setRetrying(true);
    try {
      const res = await retryAnalysisTask(Number(taskId));
      if (res.ok) {
        setTask(await res.json());
        setError("");
        // 清除旧轮询再创建新的，避免泄漏
        if (intervalRef.current) clearInterval(intervalRef.current);
        intervalRef.current = setInterval(fetchTask, 3000);
      }
    } catch {
      setError("重试失败");
    } finally {
      setRetrying(false);
    }
  };

  if (loading && !task) return <p>加载中...</p>;
  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!task) return <p>任务不存在</p>;

  const isDone = ["completed", "failed", "partial_failed"].includes(task.status);
  const canRetry = ["failed", "partial_failed"].includes(task.status);

  return (
    <div>
      <Link to={`/videos/${task.video_id}`}>← 返回视频</Link>
      <TaskProgress task={task} />

      {canRetry && (
        <button onClick={handleRetry} disabled={retrying} style={{ margin: "0.5rem 0" }}>
          {retrying ? "重试中..." : "重试失败的分P"}
        </button>
      )}

      {isDone && task.status !== "failed" && (
        <div style={{ marginTop: "1rem" }}>
          {videoSummary && (
            <div style={{ background: "#f5f5f5", padding: "1rem", borderRadius: 8, marginBottom: "1rem" }}>
              <h3>全视频总结</h3>
              <p>{videoSummary.summary}</p>
              {videoSummary.detailed_summary && (
                <>
                  <h4>详细总结</h4>
                  <p>{videoSummary.detailed_summary}</p>
                </>
              )}
              {videoSummary.key_points && videoSummary.key_points.length > 0 && (
                <>
                  <h4>全局要点</h4>
                  <ul>{videoSummary.key_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
                </>
              )}
              {videoSummary.part_overview && (
                <>
                  <h4>各分P概述</h4>
                  <ul>
                    {Object.entries(videoSummary.part_overview).map(([pn, desc]) => (
                      <li key={pn}><strong>P{pn}:</strong> {desc}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          <h3>查看分析结果</h3>
          {task.parts.filter(p => p.status === "completed").map((p) => (
            <div key={p.id}>
              <Link to={`/videos/${task.video_id}/parts/${p.video_part_id}`}>
                P{p.page_no} {p.part_title || ""} — 查看详情
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
