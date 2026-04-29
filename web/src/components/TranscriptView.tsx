import { useRef, useEffect } from "react";
import { formatTime, type TranscriptSegment } from "../types";

interface Props {
  segments: TranscriptSegment[];
  highlightTime?: number | null;
}

export default function TranscriptView({ segments, highlightTime }: Props) {
  const highlightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (highlightTime != null && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightTime]);

  if (!segments || segments.length === 0) {
    return <p>暂无文案</p>;
  }

  return (
    <div style={{ maxHeight: "60vh", overflowY: "auto" }}>
      <h3>视频文案</h3>
      {segments.map((seg, i) => {
        const isHighlighted = highlightTime != null && seg.start_time <= highlightTime && seg.end_time >= highlightTime;
        return (
          <div
            key={i}
            ref={isHighlighted ? highlightRef : null}
            style={{
              display: "flex",
              gap: "1rem",
              padding: "0.25rem 0",
              backgroundColor: isHighlighted ? "#fff3cd" : "transparent",
            }}
          >
            <span style={{ color: "#4a90d9", fontFamily: "monospace", minWidth: 60, flexShrink: 0 }}>
              {formatTime(seg.start_time)}
            </span>
            <span>{seg.text}</span>
          </div>
        );
      })}
    </div>
  );
}
