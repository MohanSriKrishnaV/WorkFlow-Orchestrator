import { Link, NavLink, Outlet } from "react-router-dom";
import { FileText, Layers, PlusCircle, ListCheck } from "lucide-react";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded px-3 py-2 text-sm ${isActive ? "bg-gray-900 text-white" : "text-gray-700 hover:bg-gray-100"}`;

export default function AppLayout() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", minHeight: "100vh" }}>
      <aside style={{ borderRight: "1px solid #e5e7eb", padding: "16px" }}>
        <div className="sidebar-brand">
          <Link to="/" className="brand-link">
            <div className="brand-mark">CSV</div>
            <div className="brand-copy">
              <span>CSV Ops</span>
              <small>Dashboard</small>
            </div>
          </Link>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/files" className={navLinkClass}>
            <FileText className="nav-icon" />
            Files
          </NavLink>
          <NavLink to="/workflows/csv-cleaning/new" className={navLinkClass}>
            <PlusCircle className="nav-icon" />
            New Workflow
          </NavLink>
          <NavLink to="/workflows" className={navLinkClass}>
            <Layers className="nav-icon" />
            Workflows
          </NavLink>
          <NavLink to="/jobs" className={navLinkClass}>
            <ListCheck className="nav-icon" />
            Jobs (optional)
          </NavLink>
        </nav>
      </aside>

      <main style={{ padding: "20px" }}>
        <Outlet />
      </main>
    </div>
  );
}