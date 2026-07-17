import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import ErrorBoundary from "./components/common/ErrorBoundary";
import "./index.css";
// Ignore missing type declarations for this side-effect font package
// @ts-ignore: Module has no type declarations
import '@fontsource/inter';
import { Toaster } from "sonner";



ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
          <Toaster richColors position="top-right" />
      <RouterProvider router={router} />
    </ErrorBoundary>
  </React.StrictMode>
);