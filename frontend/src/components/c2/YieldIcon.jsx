import { AssetIcon } from "../ui/Asset";
const names = { leaf: "plant", arrow: "arrow", chart: "chart", flask: "analytics", info: "info", reset: "refresh", check: "available" };
export default function YieldIcon({ name = "leaf", width = 20, height = width, ...props }) {
  return <AssetIcon name={names[name] || "plant"} size={width} height={height} {...props} />;
}
