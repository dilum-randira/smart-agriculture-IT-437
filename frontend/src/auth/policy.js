export const ROLES = ["admin", "researcher", "viewer"];
export const RESEARCH_ROLES = ["admin", "researcher"];
export const ROLE_LABELS = { admin: "Admin", researcher: "Researcher", viewer: "Farmer" };
const paths = new Set(["/", "/monitoring", "/predictions", "/predictions/yield", "/predictions/microclimate", "/predictions/manage", "/irrigation", "/integration", "/harvest", "/access-denied", "/farms", "/sensors", "/account"]);
function normalizedPath(value) {
  try { return decodeURIComponent(value).toLowerCase().replace(/\/+$/, "") || "/"; }
  catch { return ""; }
}

export function safeDestination(value) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u001f\u007f]/.test(value)) return "/";
  try {
    const decoded = decodeURIComponent(value);
    if (decoded.startsWith("//") || /[\\\u0000-\u001f\u007f]/.test(decoded)) return "/";
    const url = new URL(value, "http://local.invalid");
    const path = normalizedPath(url.pathname);
    if (url.origin !== "http://local.invalid" || !paths.has(path)) return "/";
    return path + url.search + url.hash;
  } catch { return "/"; }
}

export function rolesFor(path) {
  path = normalizedPath(path);
  if (path === "/predictions/manage") return ["admin"];
  if (["/irrigation", "/integration", "/harvest"].includes(path)) return RESEARCH_ROLES;
  return ROLES;
}

export function canAccess(role, path) { return rolesFor(path).includes(role); }

export function guardDecision({ status, user }, path) {
  if (status === "loading") return "loading";
  if (status === "error") return "error";
  if (!user) return "login";
  return canAccess(user.role, path) ? "allow" : "denied";
}
