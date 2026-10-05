import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AnonymousOnly, RequireAuth, RootRedirect, SessionReady } from "@/auth/guards";
import { ForgotPasswordPage } from "@/pages/forgot-password-page";
import { LoginPage } from "@/pages/login-page";
import { RegisterPage } from "@/pages/register-page";
import { ResetPasswordPage } from "@/pages/reset-password-page";
import { StatusPage } from "@/pages/status-page";
import { VerifyEmailPage } from "@/pages/verify-email-page";
import { WorkspacePage } from "@/pages/workspace-page";
import { ProjectCreatePage } from "@/pages/project-create-page";
import { ProjectEditPage } from "@/pages/project-edit-page";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";

export function App() {
  return <Routes>
    <Route path="/" element={<RootRedirect />} />
    <Route path="/status" element={<StatusPage />} />
    <Route path="/login" element={<AnonymousOnly><LoginPage /></AnonymousOnly>} />
    <Route path="/register" element={<AnonymousOnly><RegisterPage /></AnonymousOnly>} />
    <Route path="/forgot-password" element={<AnonymousOnly><ForgotPasswordPage /></AnonymousOnly>} />
    <Route path="/reset-password" element={<AnonymousOnly><ResetPasswordPage /></AnonymousOnly>} />
    <Route path="/verify-email" element={<SessionReady><VerifyEmailPage /></SessionReady>} />
    <Route path="/app" element={<RequireAuth><WorkspaceShell><Outlet /></WorkspaceShell></RequireAuth>}>
      <Route index element={<WorkspacePage />} />
      <Route path="projects/new" element={<ProjectCreatePage />} />
      <Route path="projects/:id" element={<ProjectEditPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}
