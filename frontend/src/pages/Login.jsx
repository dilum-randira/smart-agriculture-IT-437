import { useState } from "react";
import Asset, { AssetIcon, Brand } from "../components/ui/Asset";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { safeDestination } from "../auth/policy";
import { SessionState } from "../auth/RequireAuth";
import "../styles/auth.css";

export default function Login() {
  const auth = useAuth(), location = useLocation(), navigate = useNavigate();
  const [visible, setVisible] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const destination = safeDestination(location.state?.from || new URLSearchParams(location.search).get("next"));
  if (auth.status !== "ready") return <SessionState auth={auth} />;
  if (auth.user) return <Navigate to={destination} replace />;
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    const form = event.currentTarget, fields = new FormData(form);
    try { await auth.login(fields.get("username"), fields.get("password")); form.reset(); navigate(destination, { replace: true }); }
    catch (failure) { setError(failure.status === 401 ? "Unable to sign in. Check your username and password." : failure.status === 422 ? "Enter a valid username and password." : failure.message); form.elements.password.value = ""; }
    finally { setBusy(false); }
  }
  return <main className="auth-login"><section className="auth-story"><div className="auth-brand"><Brand /></div><p className="auth-eyebrow">Smart Agriculture</p><h1>Better decisions.<br /><em>Grounded in data.</em></h1><p>One workspace for agricultural intelligence, authorized farms and transparent forecasts.</p><Asset name="cropHero" className="auth-art" width={210} height={175} /><div className="auth-research-note"><b>Sample Data — Not Live Sensor Readings</b><p>Current predictions are not validated with real Sri Lankan Nai Miris field measurements.</p></div></section><section className="auth-card"><p className="auth-eyebrow"><AssetIcon name="login" size={18} />Welcome back</p><h2>Sign in to your workspace.</h2><p>Sign in to your farms and forecast insights.</p><form onSubmit={submit}><fieldset disabled={busy}><label htmlFor="login-username">Username</label><input id="login-username" name="username" autoComplete="username" required minLength={3} maxLength={64} autoCapitalize="none" spellCheck={false} /><label htmlFor="login-password">Password</label><div className="auth-password"><input id="login-password" name="password" type={visible ? "text" : "password"} autoComplete="current-password" required maxLength={128} /><button type="button" aria-controls="login-password" aria-pressed={visible} onClick={() => setVisible((value) => !value)}><AssetIcon name={visible ? "eyeOff" : "eye"} size={16} />{visible ? "Hide" : "Show"}</button></div><button className="auth-submit" type="submit">{busy ? "Signing in…" : "Sign in →"}</button></fieldset>{error && <p className="auth-error" role="alert">{error}</p>}</form><p className="auth-footnote">New to Smart Agriculture? <Link to="/register" state={{ from: destination }}>Create a Farmer account</Link>.</p></section></main>;
}
