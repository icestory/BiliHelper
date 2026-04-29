import { formatTime, type ChapterInfo } from "../types";

interface Props {
  chapters: ChapterInfo[];
  onTimeClick?: (time: number) => void;
}

export default function ChapterList({ chapters, onTimeClick }: Props) {
  if (!chapters || chapters.length === 0) return null;

  return (
    <div>
      <h3>章节</h3>
      <div>
        {chapters.map((ch, i) => (
          <div
            key={i}
            onClick={() => onTimeClick?.(ch.start_time)}
            style={{
              padding: "0.5rem",
              cursor: onTimeClick ? "pointer" : "default",
              borderLeft: "3px solid #4a90d9",
              marginBottom: "0.5rem",
            }}
          >
            <div style={{ fontWeight: "bold" }}>
              <span style={{ color: "#4a90d9", marginRight: "0.5rem" }}>
                {formatTime(ch.start_time)}
              </span>
              {ch.title}
            </div>
            {ch.description && <p style={{ color: "#666", margin: "0.25rem 0 0", fontSize: "0.9rem" }}>{ch.description}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
