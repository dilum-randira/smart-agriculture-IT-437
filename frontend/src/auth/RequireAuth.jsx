import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { guardDecision, safeDestination } from "./policy";

export function SessionState({ auth }) {
  return <main className="auth-session" role={auth.status === "error" ? "alert" : "status"}><h1>{auth.status === "error" ? "Unable to restore your session" : "Restoring your session…"}</h1>{auth.status === "error" && <><p>{auth.error}</p><button type="button" onClick={auth.refresh}>Try again</button></>}</main>;
}

export default function RequireAuth() {
  const auth = useAuth(), location = useLocation();
  const decision = guardDecision(auth, location.pathname);
  if (["loading", "error"].includes(decision)) return <SessionState auth={auth} />;
  if (decision === "login") return <Navigate to="/login" replace state={{ from: safeDestination(location.pathname + location.search + location.hash) }} />;
  if (decision === "denied") return <Navigate to="/access-denied" replace />;
  return <Outlet />;
}
