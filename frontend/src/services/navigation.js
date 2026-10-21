import { canAccess } from "../auth/policy.js";

const ITEMS = Object.freeze([
  { path: "/", shortName: "Overview" }, { path: "/farms", shortName: "My Farms" }, { path: "/monitoring", shortName: "Monitoring" },
  { path: "/predictions/microclimate", shortName: "Microclimate" }, { path: "/predictions", shortName: "Yield Prediction" },
  { path: "/sensors", shortName: "Sensors" }, { path: "/account", shortName: "Account" }, { path: "/predictions/manage", shortName: "Admin" },
]);
/** Navigation follows the existing route policy; API authorization remains server-side. */
export function navigationForRole(role) {
  return ITEMS.filter((item) => canAccess(role, item.path));
}
