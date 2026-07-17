import { createBrowserRouter, Navigate } from "react-router-dom";
import AppLayout from "../layouts/AppLayout";
import CreateWorkflowPage from "../features/workflows/pages/CreateWorkflowPage";
import FilesPage from "../features/files/pages/FilesPage";
import WorkFlowDetailsPage from "../features/workflows/pages/WorkflowDetailsPage";
import WorkFlowHomePage from "../features/workflows/pages/WorkFlowHomePage";
import LoginPage from "../features/auth/pages/LoginPage";

export const router = createBrowserRouter([
        { path: "login", element: <LoginPage /> },

  {


    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/files" replace /> },
      { path: "files", element: <FilesPage /> },
      { path: "workflows/csv-cleaning/new", element: <CreateWorkflowPage /> },
      { path: "workflows/:workflowId", element: <WorkFlowDetailsPage /> },
      { path: "workflows", element: <WorkFlowHomePage /> },
      // { path: "jobs", element: <JobsPagePlaceholder /> },
    ],
  },
]);