import { useState } from "react";
import LinkInput from "../components/LinkInput";
import VideoPreview from "../components/VideoPreview";
import type { VideoParseResponse } from "../types";

export default function VideoNewPage() {
  const [parsedData, setParsedData] = useState<VideoParseResponse | null>(null);

  if (parsedData) {
    return (
      <div>
        <button onClick={() => setParsedData(null)}>重新解析</button>
        <VideoPreview data={parsedData} />
      </div>
    );
  }

  return (
    <div>
      <h1>分析新视频</h1>
      <LinkInput onParsed={setParsedData} />
    </div>
  );
}
