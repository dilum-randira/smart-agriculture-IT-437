/** Explicit paths from the installed pack's asset-manifest.json. Never remote URLs. */
export const ASSET_BASE = "/assets/nai-miris";
export const ASSET_FILES = Object.freeze({
  brandLogo: "branding/logo-horizontal-light.svg", brandLogoDark: "branding/logo-horizontal-dark.svg", brandMark: "branding/logo-mark.svg", favicon: "branding/favicon.svg",
  avatarAdmin: "branding/avatar-admin.svg", avatarResearcher: "branding/avatar-researcher.svg", avatarFarmer: "branding/avatar-farmer.svg",
  overview: "icons/navigation/overview.svg", farms: "icons/navigation/my-farms.svg", monitoring: "icons/navigation/monitoring.svg", microclimate: "icons/navigation/microclimate.svg", yield: "icons/navigation/yield-prediction.svg", sensors: "icons/navigation/sensor-nodes.svg", account: "icons/navigation/my-account.svg", admin: "icons/navigation/admin.svg", analytics: "icons/navigation/analytics.svg", logout: "icons/navigation/logout.svg", login: "icons/navigation/login.svg", register: "icons/navigation/register.svg",
  temperature: "icons/metrics/air-temperature.svg", humidity: "icons/metrics/relative-humidity.svg", soil: "icons/metrics/soil-moisture.svg", plant: "icons/crops/plant.svg", harvest: "icons/crops/harvest.svg",
  menu: "icons/controls/menu.svg", collapse: "icons/controls/collapse.svg", arrow: "icons/controls/arrow-right.svg", chevron: "icons/controls/chevron-down.svg", calendar: "icons/controls/calendar.svg", clock: "icons/controls/clock.svg", compare: "icons/controls/compare.svg", settings: "icons/controls/settings.svg", refresh: "icons/controls/refresh.svg", eye: "icons/controls/eye.svg", eyeOff: "icons/controls/eye-off.svg", location: "icons/controls/location.svg", chart: "icons/controls/chart-line.svg", notification: "icons/controls/notification.svg",
  available: "icons/status/available.svg", warning: "icons/status/warning.svg", error: "icons/status/error.svg", info: "icons/status/info.svg", sample: "icons/status/sample-data.svg", noData: "icons/status/no-data.svg", locked: "icons/status/locked.svg",
  weatherUnknown: "weather/icons/no-data.svg",
  farmScene: "illustrations/farm/isometric-open-field.svg", cropHero: "illustrations/crops/nai-miris-pepper-hero.svg", sensorStation: "illustrations/system/sensor-station.svg", soilProfile: "illustrations/system/soil-profile.svg", historicalAnalytics: "illustrations/system/historical-weather-analytics.svg",
  noFarms: "illustrations/empty-states/no-farms.svg", noSensors: "illustrations/empty-states/no-sensors.svg", noForecast: "illustrations/empty-states/no-forecast.svg",
  surfaceNeutral: "backgrounds/surface-neutral.svg", surfaceDark: "backgrounds/surface-dark-forest.svg", surfaceCool: "backgrounds/surface-cool-blue.svg", groundBlend: "overlays/3d-ground-blend.svg", edgeFade: "overlays/edge-fade-light.svg", decorativeWaves: "overlays/forecast-waves-decorative.svg",
});
export function assetUrl(key) {
  if (!Object.hasOwn(ASSET_FILES, key)) throw new Error(`Unknown local asset: ${key}`);
  return `${ASSET_BASE}/${ASSET_FILES[key]}`;
}
export const NAV_ASSET_BY_PATH = Object.freeze({ "/": "overview", "/farms": "farms", "/monitoring": "monitoring", "/predictions/microclimate": "microclimate", "/predictions": "yield", "/predictions/yield": "yield", "/sensors": "sensors", "/account": "account", "/predictions/manage": "admin" });
export const avatarAsset = (role) => role === "admin" ? "avatarAdmin" : role === "researcher" ? "avatarResearcher" : "avatarFarmer";
