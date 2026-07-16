import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getCsvWorkflowResult, toAbsoluteDownloadUrl } from "../api/workflows.api";
import type { WorkflowResultResponse } from "../types/workflow.types";

const POLL_MS = 2500;

export default function WorkflowDetailsPage() {
  const { workflowId } = useParams();
  const id = Number(workflowId);

  const [data, setData] = useState<WorkflowResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isTerminal = useMemo(() => {
    const s = data?.workflow_status?.toUpperCase();
    return s === "SUCCESS" || s === "FAILED" || s === "CANCELLED";
  }, [data]);

  async function load() {
    if (!id || Number.isNaN(id)) return;
    try {
      if (!data) setLoading(true);
      setError(null);
      const res = await getCsvWorkflowResult(id);
      setData(res);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to fetch workflow result");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!data || isTerminal) return;
    const t = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, isTerminal, id]);

  if (!id || Number.isNaN(id)) return <p>Invalid workflow id.</p>;
  if (loading) return <p>Loading workflow...</p>;
  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <p>No workflow data.</p>;

  const downloadUrl = toAbsoluteDownloadUrl(data.cleaned_file?.download_url);

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1>Workflow #{data.workflow_id}</h1>
          <p className="page-subtitle">Current workflow progress, step details, and output file metadata.</p>
        </div>
        <span className="status-chip">{data.workflow_status}</span>
      </div>

      <section className="card panel">
        <div className="card-row">
          <div>
            <p className="section-label">Input file</p>
            <p>#{data.input_file_id}</p>
          </div>
          <div>
            <p className="section-label">Cleaned file</p>
            <p>{data.cleaned_file_id ?? "-"}</p>
          </div>
        </div>
        {data.progress && (
          <div className="card-row">
            <div>
              <p className="section-label">Progress</p>
              <p>{data.progress.steps_completed}/{data.progress.steps_total} ({data.progress.progress_percent}%)</p>
            </div>
            <div>
              <p className="section-label">Current step</p>
              <p>{data.progress.current_step}</p>
            </div>
          </div>
        )}
      </section>

      <section className="card">
        <h3>Steps</h3>
        {data.steps?.length ? (
          <ol className="steps-list">
            {data.steps
              .slice()
              .sort((a, b) => a.step_order - b.step_order)
              .map((s) => (
                <li key={`${s.step_order}-${s.step_name}`}>
                  <strong>{s.step_name}</strong>
                  <div className="steps-meta">
                    <span>{s.status}</span>
                    {s.job_id ? <span>Job #{s.job_id}</span> : null}
                    {s.job_status ? <span>{s.job_status}</span> : null}
                  </div>
                </li>
              ))}
          </ol>
        ) : (
          <p>No steps found.</p>
        )}
      </section>

      <section className="card">
        <h3>Input Profile</h3>
        <pre className="code-block">{JSON.stringify(data.input_profile ?? {}, null, 2)}</pre>
      </section>

      <section className="card">
        <h3>Cleaning Result</h3>
        <pre className="code-block">{JSON.stringify(data.cleaning_result ?? {}, null, 2)}</pre>
      </section>

      <section className="card">
        <h3>Output Profile</h3>
        <pre className="code-block">{JSON.stringify(data.output_profile ?? {}, null, 2)}</pre>
      </section>

      <section className="card">
        <h3>Cleaned File</h3>
        {data.cleaned_file ? (
          <div className="card-row file-details">
            <div>
              <p className="section-label">Name</p>
              <p>{data.cleaned_file.original_filename}</p>
            </div>
            <div>
              <p className="section-label">Type</p>
              <p>{data.cleaned_file.content_type ?? "-"}</p>
            </div>
            <div>
              <p className="section-label">Size</p>
              <p>{data.cleaned_file.size_bytes ?? "-"}</p>
            </div>
            <div>
              {downloadUrl ? (
                <a className="table-action" href={downloadUrl} target="_blank" rel="noreferrer">
                  Download cleaned file
                </a>
              ) : (
                <p>No download URL available.</p>
              )}
            </div>
          </div>
        ) : (
          <p>Not available yet.</p>
        )}
      </section>

      {data.failure && (
        <section className="card failure-card">
          <h3>Failure</h3>
          <pre className="code-block">{JSON.stringify(data.failure, null, 2)}</pre>
        </section>
      )}
    </div>
  );
}