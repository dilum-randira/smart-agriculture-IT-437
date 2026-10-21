import { useState } from "react";
import Asset, { AssetIcon, Brand } from "../components/ui/Asset";
import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { safeDestination } from "../auth/policy";
import { accessApi } from "../services/c2/accessApi";
import { SessionState } from "../auth/RequireAuth";
import "../styles/auth.css";

export default function Register() {
  const auth = useAuth(), location = useLocation();
  const destination = safeDestination(location.state?.from);
  const [visible, setVisible] = useState(false), [busy, setBusy] = useState(false);
  const [error, setError] = useState(""), [created, setCreated] = useState(false);
  if (auth.status !== "ready") return <SessionState auth={auth} />;
  if (auth.user) return <Navigate to={destination} replace />;
  async function submit(event) {
    event.preventDefault(); setError("");
    const form = event.currentTarget, fields = new FormData(form);
    if (fields.get("password") !== fields.get("confirm")) { setError("Passwords must match."); return; }
    setBusy(true);
    try {
      await accessApi("/register", { method: "POST", body: { username: fields.get("username"), password: fields.get("password") } });
      form.reset(); setCreated(true);
    } catch (failure) {
      setError(failure.status === 409 ? "This username is unavailable. Choose another username." : failure.status === 422 ? "Use a valid username and a password of 12–128 characters." : failure.message);
      form.elements.password.value = ""; form.elements.confirm.value = "";
    } finally { setBusy(false); }
  }
  return <main className="auth-login"><section className="auth-story"><div className="auth-brand"><Brand /></div><p className="auth-eyebrow">Your farm, connected</p><h1>Start with your farm.<br /><em>Grow with better insights.</em></h1><p>Create a Farmer account, add your farm details and view the sensors assigned to you.</p><Asset name="cropHero" className="auth-art" width={210} height={175} /><div className="auth-research-note"><b>Sample Data — Not Live Sensor Readings</b><p>New farms have no sensor observations until verified data is available. Sample farms require an administrator’s assignment.</p></div></section><section className="auth-card"><p className="auth-eyebrow"><AssetIcon name="register" size={18} />Farmer registration</p><h2>{created ? "Your account is ready." : "Create your account."}</h2>{created ? <div role="status"><p>Your Farmer account was saved. Sign in to add your farm. No sample farm or sensor access is granted automatically.</p><Link className="auth-submit-link" to="/login" state={{ from: destination }}>Continue to sign in</Link></div> : <><p>All new accounts receive Farmer permissions.</p><form onSubmit={submit}><fieldset disabled={busy}><label htmlFor="register-username">Username</label><input id="register-username" name="username" required minLength={3} maxLength={64} pattern="[a-zA-Z0-9_.-]+" autoComplete="username" autoCapitalize="none" spellCheck={false} aria-describedby="username-help" /><small id="username-help">3–64 letters, numbers, dots, underscores or hyphens.</small><label htmlFor="register-password">Password</label><div className="auth-password"><input id="register-password" name="password" type={visible ? "text" : "password"} required minLength={12} maxLength={128} autoComplete="new-password" aria-describedby="password-help" /><button type="button" onClick={() => setVisible((value) => !value)} aria-controls="register-password" aria-pressed={visible}><AssetIcon name={visible ? "eyeOff" : "eye"} size={16} />{visible ? "Hide" : "Show"}</button></div><small id="password-help">Use 12–128 characters and a unique password.</small><label htmlFor="register-confirm">Confirm password</label><input id="register-confirm" name="confirm" type="password" required minLength={12} maxLength={128} autoComplete="new-password" /><button className="auth-submit" type="submit">{busy ? "Creating account…" : "Create Farmer account"}</button></fieldset>{error && <p role="alert" className="auth-error">{error}</p>}</form></>}<p className="auth-footnote">Already have an account? <Link to="/login" state={{ from: destination }}>Sign in</Link></p></section></main>;
}
