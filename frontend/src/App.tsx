import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { AccessDeniedPage } from "@/pages/AccessDeniedPage";
import { AskPage } from "@/pages/AskPage";
import { LoginPage } from "@/pages/LoginPage";
import { LandingPage } from "@/pages/public/LandingPage";
import { PrivacyPage } from "@/pages/public/PrivacyPage";
import { SecurityPage } from "@/pages/public/SecurityPage";
import { TermsPage } from "@/pages/public/TermsPage";
import { useAuth } from "@/store/auth";

// The heavy analysis surfaces are only fetched when they are opened.
const DashboardPage = lazy(() => import("@/pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const DocumentsPage = lazy(() => import("@/pages/DocumentsPage").then((module) => ({ default: module.DocumentsPage })));
const DocumentDetailPage = lazy(() =>
  import("@/pages/DocumentDetailPage").then((module) => ({ default: module.DocumentDetailPage })),
);
const ContractsPage = lazy(() => import("@/pages/ContractsPage").then((module) => ({ default: module.ContractsPage })));
const ContractDetailPage = lazy(() =>
  import("@/pages/ContractDetailPage").then((module) => ({ default: module.ContractDetailPage })),
);
const SuppliersPage = lazy(() => import("@/pages/SuppliersPage").then((module) => ({ default: module.SuppliersPage })));
const SupplierDetailPage = lazy(() =>
  import("@/pages/SupplierDetailPage").then((module) => ({ default: module.SupplierDetailPage })),
);
const ComparePage = lazy(() => import("@/pages/ComparePage").then((module) => ({ default: module.ComparePage })));
const GraphPage = lazy(() => import("@/pages/GraphPage").then((module) => ({ default: module.GraphPage })));
const EvaluationPage = lazy(() =>
  import("@/pages/EvaluationPage").then((module) => ({ default: module.EvaluationPage })),
);
const SearchPage = lazy(() => import("@/pages/SearchPage").then((module) => ({ default: module.SearchPage })));
const AdminPage = lazy(() => import("@/pages/AdminPage").then((module) => ({ default: module.AdminPage })));

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuth((state) => state.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequirePermission({ permission, children }: { permission: string; children: React.ReactNode }) {
  const user = useAuth((state) => state.user);
  if (user && !user.permissions.includes(permission)) return <AccessDeniedPage permission={permission} />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      {/* Public product information */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/security" element={<SecurityPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/terms-and-conditions" element={<Navigate to="/terms" replace />} />
      </Route>

      <Route path="/login" element={<LoginPage />} />

      {/* Authenticated workspace */}
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        {/* The overview is business information: every signed-in account can read it. */}
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/ask" element={<AskPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
        <Route path="/contracts" element={<ContractsPage />} />
        <Route path="/contracts/:contractId" element={<ContractDetailPage />} />
        <Route path="/suppliers" element={<SuppliersPage />} />
        <Route path="/suppliers/:supplierId" element={<SupplierDetailPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route
          path="/graph"
          element={
            <RequirePermission permission="graph:read">
              <GraphPage />
            </RequirePermission>
          }
        />
        <Route
          path="/evaluation"
          element={
            <RequirePermission permission="evaluation:read">
              <EvaluationPage />
            </RequirePermission>
          }
        />
        {/* Administration is for accounts that can change system settings. The
            backend independently enforces admin:read / admin:write on every call
            the page makes, so hiding the route is convenience, not the control. */}
        <Route
          path="/admin"
          element={
            <RequirePermission permission="admin:write">
              <AdminPage />
            </RequirePermission>
          }
        />
        <Route path="*" element={<Navigate to="/ask" replace />} />
      </Route>
    </Routes>
  );
}
