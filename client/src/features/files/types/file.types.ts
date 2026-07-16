export type FileItem = {
  id: number;
  original_filename: string;
  content_type?: string | null;
  size_bytes?: number | null;
  created_at?: string;
};