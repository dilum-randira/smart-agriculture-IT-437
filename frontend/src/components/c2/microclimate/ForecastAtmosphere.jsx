import Asset from "../../ui/Asset";
import ClimateIcon from "./ClimateIcon";
import { forecastVisualContext, sparklinePoints } from "../../../services/c2/forecastVisuals";

export default function ForecastAtmosphere({ predictions, horizon }) {
  const context = forecastVisualContext(predictions, horizon);
  return <div className={`mc-atmosphere ${context.tone}`} aria-label="Forecast environmental context">
    <div className="mc-atmosphere-orbits" aria-hidden="true"><i /><i /><i /><span /></div>
    <div className="mc-atmosphere-label"><span className="mc-status-dot" />{context.temperature ? `MODEL OUTLOOK · ${horizon} HOURS` : "ENVIRONMENTAL INTELLIGENCE"}</div>
    <div className="mc-atmosphere-icon"><ClimateIcon name={context.tone === "humid" ? "humidity" : context.tone === "warm" ? "temperature" : "leaf"} size={44} /></div>
    <h2>{context.label}</h2>
    <div className="mc-atmosphere-readings"><div><span>Air temperature</span><strong>{context.temperature ? context.temperature.mean.toFixed(1) : "—"}<small>°C</small></strong></div><div><span>Relative humidity</span><strong>{context.humidity ? context.humidity.mean.toFixed(1) : "—"}<small>%</small></strong></div></div>
    {context.temperature && <svg viewBox="0 0 240 48" className="mc-atmosphere-trend" role="img" aria-label={`${horizon}-hour air temperature forecast trend, relative scale`}><polyline points={sparklinePoints(predictions.slice(0, horizon), "air_temperature_c")} fill="none" stroke="currentColor" strokeWidth="1.8" vectorEffect="non-scaling-stroke" /></svg>}
    <p>{context.temperature ? "Horizon means · Model predictions, not measurements" : "Select your node and run a forecast to reveal the outlook."}</p>
    <small className="mc-weather-unknown"><Asset name="weatherUnknown" width={18} height={18} />Weather conditions not supplied · No rain or cloud prediction</small>
  </div>;
}
