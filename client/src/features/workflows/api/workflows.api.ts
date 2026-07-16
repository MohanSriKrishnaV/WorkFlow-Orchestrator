import { api } from "../../../lib/axios";
import type {
  CreateCsvWorkflowRequest,
  CreateCsvWorkflowResponse,
} from "../types/workflow.types";


import type { WorkflowResultResponse } from "../types/workflow.types";



export async function createCsvCleaningWorkflow(
  payload: CreateCsvWorkflowRequest
): Promise<CreateCsvWorkflowResponse> {
  const res = await api.post("/workflows/csv-cleaning", payload);
  return res.data;
}



export async function getCsvWorkflowResult(
  workflowId: number
): Promise<WorkflowResultResponse> {
  const res = await api.get(`/workflows/${workflowId}/result`);
  return res.data;
}

export function toAbsoluteDownloadUrl(relativeOrAbsolute?: string): string | null {
  if (!relativeOrAbsolute) return null;
  if (relativeOrAbsolute.startsWith("http://") || relativeOrAbsolute.startsWith("https://")) {
    return relativeOrAbsolute;
  }
  const base = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1").replace(/\/$/, "");
  const root = base.replace(/\/api\/v1$/, "");
  return `${root}${relativeOrAbsolute.startsWith("/") ? "" : "/"}${relativeOrAbsolute}`;
}