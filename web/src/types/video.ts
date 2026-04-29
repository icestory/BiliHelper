export interface PartInfo {
  id: number | null;
  page_no: number;
  cid: number | null;
  title: string | null;
  duration: number | null;
  source_url: string | null;
}

export interface VideoInfo {
  id: number | null;
  bvid: string;
  aid: number | null;
  title: string;
  owner_name: string | null;
  cover_url: string | null;
  duration: number | null;
  description: string | null;
  published_at: string | null;
  part_count: number;
  source_url: string | null;
}

export interface VideoParseResponse {
  video: VideoInfo;
  parts: PartInfo[];
  already_analyzed: boolean;
}

export interface VideoHistoryItem {
  id: number;
  bvid: string;
  title: string;
  owner_name: string | null;
  cover_url: string | null;
  part_count: number;
  created_at: string;
}

export interface VideoHistoryResponse {
  items: VideoHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface VideoDetailResponse extends VideoInfo {
  parts: PartInfo[];
  created_at: string;
}
