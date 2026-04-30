export interface PartAnalysisStatus {
  id: number;
  video_part_id: number;
  page_no: number | null;
  part_title: string | null;
  status: string;
  transcript_source: string | null;
  progress: number;
  error_message: string | null;
}

export interface AnalysisTaskResponse {
  id: number;
  video_id: number;
  status: string;
  progress: number;
  error_message: string | null;
  parts: PartAnalysisStatus[];
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface TranscriptSegment {
  start_time: number;
  end_time: number;
  text: string;
  source: string;
}

export interface PartAnalysisDetail {
  id: number;
  video_part_id: number;
  status: string;
  transcript_source: string | null;
  transcript_segments: TranscriptSegment[] | null;
  summary: {
    summary: string;
    detailed_summary: string;
    key_points: string[];
  } | null;
  chapters: ChapterInfo[] | null;
  error_message: string | null;
}

export interface ChapterInfo {
  start_time: number;
  end_time: number | null;
  title: string;
  description: string;
  keywords: string[];
}

/** 将秒数转为 mm:ss 格式 */
export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "00:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

/** 任务状态中文映射 */
export const STATUS_LABELS: Record<string, string> = {
  waiting: "等待中",
  fetching_subtitle: "正在获取字幕",
  extracting_audio: "正在提取音频",
  transcribing: "正在进行语音识别",
  asr: "正在进行语音识别",
  summarizing: "正在生成总结",
  completed: "已完成",
  failed: "失败",
  running: "运行中",
  partial_failed: "部分失败",
};
