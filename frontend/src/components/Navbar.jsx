import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { ROLE_LABELS } from "../auth/policy";
import Asset, { AssetIcon, Brand } from "./ui/Asset";
import { avatarAsset, NAV_ASSET_BY_PATH } from "../services/uiAssets";
import "../styles/navigation.css";

export default function Navbar({ navigation }) {
  const [isOpen, setIsOpen] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const location = useLocation(), navigate = useNavigate(), auth = useAuth();
  const sidebar = useRef(null), menuButton = useRef(null), account = useRef(null);
  const active = navigation.find((item) => item.path === location.pathname || item.path === "/predictions" && location.pathname === "/predictions/yield");
  useEffect(() => { setIsOpen(false); if (account.current) account.current.open = false; }, [location.pathname]);
  useEffect(() => {
    const wide = window.matchMedia("(min-width:1101px)");
    const sync = () => { if (wide.matches) setIsOpen(false); };
    wide.addEventListener("change", sync); return () => wide.removeEventListener("change", sync);
  }, []);
  useEffect(() => {
    if (!isOpen) return;
    const previous = document.activeElement, oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const items = () => [...sidebar.current.querySelectorAll('a,button')].filter((item) => item.getClientRects().length);
    items()[0]?.focus();
    const keydown = (event) => {
      if (event.key === "Escape") { setIsOpen(false); return; }
      if (event.key !== "Tab") return;
      const list = items(), first = list[0], last = list.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", keydown);
    return () => { document.body.style.overflow = oldOverflow; document.removeEventListener("keydown", keydown); previous?.focus(); };
  }, [isOpen]);
  useEffect(() => {
    const close = (event) => { if (account.current && !account.current.contains(event.target)) account.current.open = false; };
    const escape = (event) => { if (event.key === "Escape" && account.current?.open) { account.current.open = false; account.current.querySelector("summary")?.focus(); } };
    document.addEventListener("pointerdown", close); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", close); document.removeEventListener("keydown", escape); };
  }, []);
  async function signOut() {
    setBusy(true); setError("");
    try { await auth.logout(); navigate("/login", { replace: true }); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <>
    {isOpen && <button className="app-drawer-scrim" type="button" tabIndex={-1} aria-label="Close navigation" onClick={() => setIsOpen(false)} />}
    <aside className={`app-sidebar ${isOpen ? "is-open" : ""}`} ref={sidebar} aria-label="Application sidebar" role={isOpen ? "dialog" : undefined} aria-modal={isOpen || undefined}>
      <div className="app-sidebar-brand"><Link to="/" aria-label="Nai Miris overview"><Brand /></Link><button type="button" className="app-drawer-close" aria-label="Close navigation menu" onClick={() => setIsOpen(false)}><AssetIcon name="collapse" /></button></div>
      <p className="app-nav-caption">FARM WORKSPACE</p>
      <nav id="primary-navigation" aria-label="Main navigation">{navigation.map((item) => <NavLink key={item.path} to={item.path} end={item.path === "/" || item.path === "/predictions"} onClick={() => setIsOpen(false)} className={({ isActive }) => `app-nav-link ${isActive ? "is-active" : ""}`}><AssetIcon name={NAV_ASSET_BY_PATH[item.path] || "overview"} size={21} /><span>{item.shortName}</span></NavLink>)}</nav>
      <div className="app-sidebar-context"><AssetIcon name="info" size={18} /><div><strong>Clear data. Better decisions.</strong><p>Source labels distinguish sample observations from live readings.</p></div></div>
      <div className="app-sidebar-account"><Asset name={avatarAsset(auth.user.role)} width={32} height={32} /><span><strong>{ROLE_LABELS[auth.user.role]}</strong><small>Authorized workspace</small></span><AssetIcon name="locked" size={16} /></div>
    </aside>
    <header className="app-topbar"><div className="app-topbar-heading"><button ref={menuButton} type="button" className="app-menu-button" aria-controls="primary-navigation" aria-expanded={isOpen} aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"} onClick={() => setIsOpen((value) => !value)}><AssetIcon name="menu" /><span>Menu</span></button><div><span className="app-topbar-eyebrow">SMART AGRICULTURE</span><p>{active?.shortName || "Workspace"}</p></div></div>
      <details className="app-account-dropdown" ref={account}><summary><Asset name={avatarAsset(auth.user.role)} width={38} height={38} /><span className="app-profile-identity"><strong>{auth.user.username}</strong><small>{ROLE_LABELS[auth.user.role]}</small></span><AssetIcon name="chevron" size={15} /></summary><div className="app-account-menu"><span>Signed in as <strong>{auth.user.username}</strong></span><Link to="/account"><AssetIcon name="account" size={18} />Your account</Link><button type="button" onClick={signOut} disabled={busy}><AssetIcon name="logout" size={18} />{busy ? "Signing out..." : "Logout"}</button>{error && <p role="alert">{error}</p>}</div></details>
    </header>
  </>;
}
