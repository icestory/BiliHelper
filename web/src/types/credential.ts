export interface ApiCredentialResponse {
  id: number;
  provider: string;
  api_base_url: string | null;
  api_key_masked: string;
  default_model: string | null;
  default_asr_model: string | null;
  default_embedding_model: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}
