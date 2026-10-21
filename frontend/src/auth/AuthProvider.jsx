import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { accessApi } from "../services/c2/accessApi";
import { ROLES } from "./policy";

export const AuthContext = createContext(null);
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("Authentication provider is required");
  return context;
}

export default function AuthProvider({ children }) {
  const [state, setState] = useState({ user: null, status: "loading", error: "" });
  const revision = useRef(0);
  const location = useLocation();
  const restore = useCallback(async (signal, background = false) => {
    const turn = ++revision.current;
    if (!background) setState((old) => ({ ...old, status: "loading", error: "" }));
    try {
      const data = await accessApi("/me", { signal });
      if (!ROLES.includes(data.user?.role)) throw new Error("Unsupported account role; contact an administrator.");
      if (!signal?.aborted && turn === revision.current) setState({ user: data.user, status: "ready", error: "" });
    } catch (error) {
      if (!signal?.aborted && turn === revision.current) setState({ user: null, status: error.status === 401 ? "ready" : "error", error: error.status === 401 ? "" : error.message });
    }
  }, []);
  useEffect(() => { const controller = new AbortController(); restore(controller.signal); return () => controller.abort(); }, [restore, location.pathname]);
  useEffect(() => {
    const expired = () => { revision.current++; setState({ user: null, status: "ready", error: "" }); };
    const focus = () => { restore(undefined, true); };
    window.addEventListener("c2:session-expired", expired);
    window.addEventListener("focus", focus);
    return () => { window.removeEventListener("c2:session-expired", expired); window.removeEventListener("focus", focus); };
  }, [restore]);
  async function login(username, password) {
    const data = await accessApi("/login", { method: "POST", body: { username, password } });
    if (!ROLES.includes(data.user?.role)) throw new Error("Unsupported account role; contact an administrator.");
    revision.current++; setState({ user: data.user, status: "ready", error: "" });
  }
  async function logout() {
    try { await accessApi("/logout", { method: "POST" }); }
    catch (error) { if (error.status !== 401) throw error; }
    revision.current++; setState({ user: null, status: "ready", error: "" });
  }
  return <AuthContext.Provider value={{ ...state, login, logout, refresh: () => restore() }}>{children}</AuthContext.Provider>;
}
