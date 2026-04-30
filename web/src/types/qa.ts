export interface CitationInfo {
  part_id: number | null;
  page_no: number | null;
  start_time: number;
  end_time: number | null;
  text: string | null;
}

export interface QAMessageResponse {
  id: number;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  citations: CitationInfo[] | null;
  created_at: string;
}

export interface QASessionResponse {
  id: number;
  video_id: number;
  title: string | null;
  scope: string;
  selected_part_ids: number[] | null;
  created_at: string;
}
