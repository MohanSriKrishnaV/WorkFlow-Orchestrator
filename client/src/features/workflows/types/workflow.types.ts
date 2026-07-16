export type CsvCleanOptions = {
  drop_missing_rows: boolean;
  trim_whitespace: boolean;
  lowercase_headers: boolean;
};

export type CreateCsvWorkflowRequest = {
  input_file_id: number;
  clean_options: CsvCleanOptions;
};

export type CreateCsvWorkflowResponse = {
  workflow_id: number;
  first_job_id?: number;
};



export type WorkflowStep = {
  step_name: string;
  step_order: number;
  status: string;
  job_id?: number | null;
  job_status?: string | null;
};

export type WorkflowResultResponse = {
  workflow_id: number;
  workflow_status: string;
  input_file_id: number;
  cleaned_file_id?: number | null;

  input_profile?: Record<string, any> | null;
  cleaning_result?: Record<string, any> | null;
  output_profile?: Record<string, any> | null;

  steps: WorkflowStep[];
  cleaned_file?: {
    id: number;
    original_filename: string;
    storage_path?: string;
    content_type?: string;
    size_bytes?: number;
    download_url?: string;
  } | null;

  progress?: {
    steps_total: number;
    steps_completed: number;
    progress_percent: number;
    current_step: string;
  };

  failure?: {
    failed_step?: string;
    error_message?: string;
  } | null;
};