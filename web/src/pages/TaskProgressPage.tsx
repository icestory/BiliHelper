import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { getAnalysisTask } from "../api/analysis";
import TaskProgress from "../components/TaskProgress";
import type { AnalysisTaskResponse } from "../types";

export default function TaskProgressPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [task, setTask] = useState<AnalysisTaskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
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
      // 任务完成或失败后停止轮询
      if (["completed", "failed", "partial_failed"].includes(data.status)) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
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
    // 每 3 秒轮询一次
    intervalRef.current = setInterval(fetchTask, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId]);

  if (loading && !task) return <p>加载中...</p>;
  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!task) return <p>任务不存在</p>;

  const isDone = ["completed", "failed", "partial_failed"].includes(task.status);

  return (
    <div>
      <Link to={`/videos/${task.video_id}`}>← 返回视频</Link>
      <TaskProgress task={task} />
      {isDone && task.status !== "failed" && (
        <div style={{ marginTop: "1rem" }}>
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
