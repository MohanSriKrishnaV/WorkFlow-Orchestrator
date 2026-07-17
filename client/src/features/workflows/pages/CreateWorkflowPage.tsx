import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listFiles } from "../../files/api/files.api";
import type { FileItem } from "../../files/types/file.types";
import { createCsvCleaningWorkflow } from "../api/workflows.api";

export default function CreateWorkflowPage() {
  const navigate = useNavigate();

  const [files, setFiles] = useState<FileItem[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [inputFileId, setInputFileId] = useState<number | "">("");
  const [dropMissingRows, setDropMissingRows] = useState(true);
  const [trimWhitespace, setTrimWhitespace] = useState(true);
  const [lowercaseHeaders, setLowercaseHeaders] = useState(false);
  const [removeEmptyRows, setRemoveEmptyRows] = useState(true);
  const [removeDuplicateRows, setRemoveDuplicateRows] = useState(true);
  const [normalizeColumnNames, setNormalizeColumnNames] = useState(true);
  const [removeEmptyColumns, setRemoveEmptyColumns] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setLoadingFiles(true);
        const data = await listFiles();
        setFiles(data);
      } catch {
        setError("Failed to load files");
      } finally {
        setLoadingFiles(false);
      }
    })();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!inputFileId) {
      setError("Please select an input file.");
      return;
    }

    if(!dropMissingRows && !trimWhitespace && !lowercaseHeaders && !removeEmptyRows && !removeDuplicateRows && !normalizeColumnNames && !removeEmptyColumns) {
      setError("Please select at least one cleaning option.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const res = await createCsvCleaningWorkflow({
        input_file_id: Number(inputFileId),
        clean_options: {
          drop_missing_rows: dropMissingRows,
          trim_whitespace: trimWhitespace,
          lowercase_headers: lowercaseHeaders,
          remove_empty_rows: removeEmptyRows,
          remove_duplicate_rows: removeDuplicateRows,
          normalize_column_names: normalizeColumnNames,
          remove_empty_columns: removeEmptyColumns,
        },
      });

      navigate(`/workflows/${res.workflow_id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to create workflow");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1>New CSV Cleaning Workflow</h1>
          <p className="page-subtitle">Choose a source file and cleaning options to start processing.</p>
        </div>
      </div>

      <div className="card panel">
        <form className="workflow-form" onSubmit={onSubmit}>
          <label className="form-field">
            Input file
            {loadingFiles ? (
              <span>Loading files...</span>
            ) : (
              <select
                className="select-field"
                value={inputFileId}
                onChange={(e) => setInputFileId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">Select file...</option>
                {files.map((f) => (
                  <option key={f.id} value={f.id}>
                    #{f.id} - {f.original_filename}
                  </option>
                ))}
              </select>
            )}
          </label>

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={dropMissingRows}
              onChange={(e) => setDropMissingRows(e.target.checked)}
            />
            Drop rows with missing values
          </label>

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={trimWhitespace}
              onChange={(e) => setTrimWhitespace(e.target.checked)}
            />
            Trim whitespace
          </label>

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={lowercaseHeaders}
              onChange={(e) => setLowercaseHeaders(e.target.checked)}
            />
            Lowercase headers
          </label>


<label className="checkbox-field">
  <input
    type="checkbox"
    checked={removeEmptyRows}
    onChange={(e) => setRemoveEmptyRows(e.target.checked)}
  />
  Remove empty rows
</label>


<label className="checkbox-field">
  <input
    type="checkbox"
    checked={removeDuplicateRows}
    onChange={(e) => setRemoveDuplicateRows(e.target.checked)}
  />
  Remove duplicate rows
</label>


<label className="checkbox-field">
  <input
    type="checkbox"
    checked={normalizeColumnNames}
    onChange={(e) => setNormalizeColumnNames(e.target.checked)}
  />
  Normalize column names
</label>

<label className="checkbox-field">
  <input
    type="checkbox"
    checked={removeEmptyColumns}
    onChange={(e) => setRemoveEmptyColumns(e.target.checked)}
  />
  Remove empty columns
</label>

          {error && <p className="form-error">{error}</p>}

          <button className="primary-btn" type="submit" disabled={submitting || loadingFiles}>
            {submitting ? "Creating..." : "Create Workflow"}
          </button>
        </form>
      </div>
    </div>
  );
}