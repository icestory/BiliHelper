import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { listQASessions, createQASession, getQAMessages, askQuestion } from "../api/qa";
import { formatTime, type QASessionResponse, type QAMessageResponse } from "../types";

export default function QAPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const [sessions, setSessions] = useState<QASessionResponse[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<QAMessageResponse[]>([]);
  const [input, setInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!videoId) return;
    listQASessions(Number(videoId))
      .then(r => r.ok ? r.json() : [])
      .then(setSessions)
      .catch(() => {});
  }, [videoId]);

  useEffect(() => {
    if (!activeSessionId) return;
    getQAMessages(activeSessionId)
      .then(r => r.ok ? r.json() : [])
      .then(setMessages)
      .catch(() => {});
  }, [activeSessionId]);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleCreateSession = async () => {
    const res = await createQASession(Number(videoId), undefined, "video");
    if (res.ok) {
      const s = await res.json();
      setSessions([s, ...sessions]);
      setActiveSessionId(s.id);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !activeSessionId) return;
    setSubmitting(true);
    try {
      const res = await askQuestion(activeSessionId, input.trim());
      if (res.ok) {
        const msg = await res.json();
        setMessages(prev => [...prev, msg]);
        setInput("");
      }
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <Link to={`/videos/${videoId}`}>← 返回视频</Link>
      <h1>视频问答</h1>

      <div style={{ display: "flex", gap: "1rem" }}>
        <div style={{ width: 200, flexShrink: 0 }}>
          <button onClick={handleCreateSession}>+ 新建会话</button>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {sessions.map(s => (
              <li
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                style={{
                  padding: "0.5rem",
                  cursor: "pointer",
                  backgroundColor: s.id === activeSessionId ? "#e8f0fe" : "transparent",
                }}
              >
                {s.title || `会话 ${s.id}`}
                <br />
                <small>{s.created_at}</small>
              </li>
            ))}
          </ul>
        </div>

        <div style={{ flex: 1 }}>
          {activeSessionId ? (
            <>
              <div style={{ maxHeight: "60vh", overflowY: "auto", border: "1px solid #eee", padding: "1rem", borderRadius: 8 }}>
                {messages.map(m => (
                  <div key={m.id} style={{ marginBottom: "1rem" }}>
                    <strong>{m.role === "user" ? "你" : "AI"}</strong>
                    <p style={{ whiteSpace: "pre-wrap" }}>{m.content}</p>
                    {m.citations && m.citations.length > 0 && (
                      <div style={{ fontSize: "0.85rem", color: "#666" }}>
                        引用：
                        {m.citations.map((c, i) => (
                          <span key={i} style={{ marginRight: "0.5rem" }}>
                            {c.page_no ? `P${c.page_no} ` : ""}
                            {formatTime(c.start_time)}
                            {c.end_time ? `-${formatTime(c.end_time)}` : ""}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messagesEnd} />
              </div>

              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleSend()}
                  placeholder="输入问题..."
                  style={{ flex: 1, padding: "0.5rem" }}
                  disabled={submitting}
                />
                <button onClick={handleSend} disabled={submitting || !input.trim()}>
                  {submitting ? "发送中..." : "发送"}
                </button>
              </div>
            </>
          ) : (
            <p>选择一个会话或创建新会话开始问答</p>
          )}
        </div>
      </div>
    </div>
  );
}
