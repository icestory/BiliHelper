interface Props {
  videoId: number;
  partId?: number;  // 为 null 时导出全视频
}

export default function ExportMenu({ videoId, partId }: Props) {
  const downloadMd = (includeTranscript: boolean, includeChapters: boolean, includeQA = false) => {
    const base = `/api/exports`;
    const path = partId
      ? `${base}/parts/${partId}.md`
      : `${base}/videos/${videoId}.md`;
    const params = new URLSearchParams();
    params.set("include_transcript", String(includeTranscript));
    params.set("include_chapters", String(includeChapters));
    if (!partId) params.set("include_qa", String(includeQA));
    const url = `${path}?${params.toString()}`;
    window.open(url, "_blank");
  };

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: "1rem" }}>
      <h3>导出 Markdown</h3>
      <button onClick={() => downloadMd(true, true, !partId)}>导出完整内容（含文案+章节{!partId ? "+问答" : ""})</button>
      <button onClick={() => downloadMd(false, true)} style={{ marginLeft: "0.5rem" }}>仅总结和章节</button>
      <button onClick={() => downloadMd(true, false)} style={{ marginLeft: "0.5rem" }}>仅总结和文案</button>
    </div>
  );
}
