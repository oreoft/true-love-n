import { Outlet } from "react-router-dom";

// Local controller-only mode: no cloud auth server.
// The controller is a single-user local service — skip session checks entirely.
export function AuthLayout() {
  return <Outlet />;
}
