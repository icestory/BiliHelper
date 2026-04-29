import type { AnalysisTaskResponse } from "../types";
import { STATUS_LABELS } from "../types";

interface Props {
  task: AnalysisTaskResponse;
}

export default function TaskProgress({ task }: Props) {
  return (
    <div>
      <h2>分析进度</h2>
      <p>状态：{STATUS_LABELS[task.status] || task.status}</p>
      <p>总进度：{task.progress}%</p>
      {task.error_message && <p style={{ color: "red" }}>错误：{task.error_message}</p>}

      <div style={{ marginTop: "1rem" }}>
        {task.parts.map((part) => (
          <div key={part.id} style={{ padding: "0.5rem", border: "1px solid #eee", marginBottom: "0.5rem", borderRadius: 4 }}>
            <strong>P{part.page_no} {part.part_title || ""}</strong>
            <span style={{ marginLeft: "0.5rem", color: part.status === "completed" ? "green" : part.status === "failed" ? "red" : "#666" }}>
              {STATUS_LABELS[part.status] || part.status}
            </span>
            {part.transcript_source && <span style={{ marginLeft: "0.5rem", fontSize: "0.85rem", color: "#999" }}>（{part.transcript_source === "bili_subtitle" ? "B站字幕" : "语音识别"}）</span>}
            {part.error_message && <p style={{ color: "red", fontSize: "0.85rem" }}>{part.error_message}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
