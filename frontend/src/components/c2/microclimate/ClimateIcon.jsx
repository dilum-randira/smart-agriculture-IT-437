import { AssetIcon } from "../../ui/Asset";
const names = { leaf: "plant", temperature: "temperature", humidity: "humidity", soil: "soil", arrow: "arrow", layers: "analytics", clock: "clock", compare: "compare", info: "info" };
export default function ClimateIcon({ name = "leaf", size = 20, ...props }) {
  return <AssetIcon name={names[name] || "plant"} size={size} {...props} />;
}
