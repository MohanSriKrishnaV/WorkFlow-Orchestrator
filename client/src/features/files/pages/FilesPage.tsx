import { useEffect, useState } from "react";
import { getDownloadUrl, listFiles, uploadFile } from "../api/files.api";
import type { FileItem } from "../types/file.types";

export default function FilesPage() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const data = await listFiles();
      setFiles(data);
    } catch (e) {
      setError("Failed to load files");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if(file && file.type !== "text/csv") {
      setError("Only CSV files are allowed");
      e.target.value = "";
      return;
    }
    if (!file) return;
    try {
      setUploading(true);
      setError(null);
      await uploadFile(file);
      await load();
      e.target.value = "";
    } catch {
      setError("Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1>Files</h1>
          <p className="page-subtitle">Upload CSV files and manage dataset assets from one place.</p>
        </div>
      </div>

      <div className="card panel">
        <div className="form-row">
          <label className="file-upload">
            Choose a CSV file
            <input type="file" accept=".csv,text/csv" onChange={onPickFile} disabled={uploading} />
          </label>
          {uploading && <p>Uploading...</p>}
        </div>

        {error && <p className="form-error">{error}</p>}

        {loading ? (
          <p>Loading files...</p>
        ) : files.length === 0 ? (
          <div className="card-empty">No files uploaded yet.</div>
        ) : (
          <table className="data-table" cellPadding={8}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Filename</th>
                <th>Type</th>
                <th>Size</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.id}>
                  <td>{f.id}</td>
                  <td>{f.original_filename}</td>
                  <td>{f.content_type ?? "-"}</td>
                  <td>{f.size_bytes ?? "-"}</td>
                  <td>
                    <a className="table-action" href={getDownloadUrl(f.id)} target="_blank" rel="noreferrer">
                      Download
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}