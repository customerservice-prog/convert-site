export interface NormalizedChoice {
  key: string;
  label: string;
  description?: string;
  format_id: string;
  output_type: string;
  container?: string;
}

export interface FormatRow {
  format_id: string;
  resolution?: string | null;
  height?: number | null;
  ext?: string;
  vcodec?: string;
  acodec?: string;
  filesize?: number | null;
}

export interface MetadataResponse {
  title?: string | null;
  thumbnail?: string | null;
  duration?: number | null;
  duration_label?: string | null;
  source_site?: string | null;
  uploader?: string | null;
  upload_date?: string | null;
  description?: string | null;
  formats: FormatRow[];
  normalized_choices: NormalizedChoice[];
  recommended_choice_key?: string;
  default_format_id?: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  status_label?: string;
  progress: number;
  stage?: string;
  title?: string | null;
  output_type?: string;
  thumbnail_url?: string | null;
  error?: string;
  code?: string;
  expires_at?: string;
  download_url?: string | null;
  filename?: string | null;
  file_size?: number | null;
}

export type UiFlowPhase =
  | "initial"
  | "analyzing"
  | "metadata_ready"
  | "creating_job"
  | "job_tracking"
  | "network_retry";
