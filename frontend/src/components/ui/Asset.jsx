import { assetUrl } from "../../services/uiAssets";
import "../../styles/assets.css";

export default function Asset({ name, alt = "", className = "", width = 24, height = width, loading = "lazy", ...props }) {
  return <img src={assetUrl(name)} alt={alt} aria-hidden={alt ? undefined : true} className={`ui-asset ${className}`} width={width} height={height} loading={loading} decoding="async" {...props} />;
}
export function AssetIcon({ name, size = 20, className = "", ...props }) {
  return <Asset name={name} className={`ui-icon ${className}`} width={size} height={size} loading="eager" {...props} />;
}
export function Brand({ dark = false, className = "" }) {
  // The supplied horizontal SVG has generous transparent canvas on its right.
  // Crop only its viewport in CSS; retain the original file and accessible logo.
  return <span className={`ui-brand ${className}`}><Asset name={dark ? "brandLogoDark" : "brandLogo"} alt="Nai Miris Smart Agriculture" width={610} height={124} loading="eager" /></span>;
}
