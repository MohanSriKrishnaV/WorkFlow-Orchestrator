import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../../lib/axios";

type WorkflowListItem = {
  id: number;
  name?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
};

export default function WorkFlowHomePage() {
  const navigate = useNavigate();

  const [rows, setRows] = useState<WorkflowListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadWorkflows() {
    try {
      setLoading(true);
      setError(null);

      // adjust endpoint if your backend route differs
      const res = await api.get("/workflows", { params: { limit: 50, offset: 0 } });

      // supports either plain array or paginated shape
      const data = Array.isArray(res.data) ? res.data : (res.data?.items ?? []);
      setRows(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkflows();
  }, []);

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1>Workflows</h1>
          <p className="page-subtitle">Track pipeline runs and inspect status details.</p>
        </div>
        <button className="primary-btn secondary-btn" onClick={() => navigate("/workflows/csv-cleaning/new")}>+ New Workflow</button>
      </div>

      {loading && <p>Loading workflows...</p>}
      {error && <p className="form-error">{error}</p>}

      {!loading && !error && rows.length === 0 && (
        <div className="card">No workflows found.</div>
      )}

      {!loading && !error && rows.length > 0 && (
        <div className="card panel">
          <table className="data-table" cellPadding={8}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Status</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((wf) => (
                <tr key={wf.id}>
                  <td>{wf.id}</td>
                  <td>{wf.name ?? "csv_cleaning_pipeline"}</td>
                  <td><span className="status-chip">{wf.status}</span></td>
                  <td>{wf.created_at ?? "-"}</td>
                  <td>
                    <button className="table-action" onClick={() => navigate(`/workflows/${wf.id}`)}>
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}