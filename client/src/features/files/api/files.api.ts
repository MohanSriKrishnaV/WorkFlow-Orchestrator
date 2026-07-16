import { api } from "../../../lib/axios";
import type { FileItem } from "../types/file.types";

export async function listFiles(): Promise<FileItem[]> {
  const res = await api.get("/files");
  debugger;
  console.log(res,"res")
  return res.data;
}

export async function uploadFile(file: File): Promise<FileItem> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post("/files/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export function getDownloadUrl(fileId: number): string {
  const base = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
  return `${base}/files/${fileId}/download`;
}