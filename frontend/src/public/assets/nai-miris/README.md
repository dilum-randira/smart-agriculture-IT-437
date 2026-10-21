# Nai Miris Smart Agriculture — Web Asset Kit

Original SVG + PNG asset collection for the existing **React/Vite + FastAPI** application, designed for an **open-field Capsicum chinense / Nai Miris** forecasting interface.

## Install — no package installation needed

1. Unzip the downloaded archive.
2. Copy its **`nai-miris`** folder into `frontend/public/assets/`.
3. The final folder should be `frontend/public/assets/nai-miris/`. Keep subfolders unchanged.
4. In React, reference files using URL paths such as:

```jsx
<img src="/assets/nai-miris/weather/icons/partly-cloudy.svg" alt="Partly cloudy" />
<img src="/assets/nai-miris/icons/metrics/air-temperature.svg" alt="" aria-hidden="true" />
<img src="/assets/nai-miris/illustrations/farm/isometric-open-field.svg" alt="Illustrated open-field farm" />
```

Alternative: copy the **contents** of `nai-miris/` directly into `frontend/public/assets/nai-miris/`.

### Folder structure

```text
nai-miris/
├─ branding/                Original mark, wordmarks, role avatars, favicon
├─ icons/
│  ├─ navigation/           App/sidebar and role icons
│  ├─ metrics/              Weather, soil, rainfall and energy icons
│  ├─ controls/             App action icons
│  ├─ crops/                Plant and irrigation icons
│  └─ status/               Available, warning, stale, no-data etc.
├─ weather/icons/           16 weather condition icons (SVG + PNG)
├─ illustrations/
│  ├─ farm/                 Isometric outdoor farm fallback/contextual visual
│  ├─ crops/                Pepper hero and 6 crop stages
│  ├─ system/               Node, soil profile, historical data
│  └─ empty-states/         Empty farm, node, forecasts
├─ backgrounds/            6 weather scenes + 5 page surface backgrounds
├─ overlays/               Three.js background blending, edge fade, waves
├─ docs/                   CSS tokens and machine-readable asset manifest
└─ preview/                Overview image of the actual kit
```

## Design guidance

- Use **neutral white** as the main UI background. Forest green is the brand, not every card background.
- Temperature **amber**; humidity and rainfall **blue**; soil moisture **leaf green**.
- Keep existing real model charts and control logic. These assets are visual resources only.
- `illustrations/farm/isometric-open-field.svg` is a **static illustration**, **not** a replacement for the app's interactive Three.js scene.
- `overlays/3d-ground-blend.svg` can visually blend the existing Three.js canvas with a neutral page background.
- Weather-condition icons for rainy/cloudy/sunny may be displayed as **weather claims only when a verified source provides that condition**. Do NOT infer rain from high RH alone. Otherwise show neutral visuals/icons.
- Decorative wave art is **not data**. Never use it as a forecast chart. Preserve original 336-hour history and 24/72/168-hour forecast charts.
- Dataset and model limitations must remain available to users: the current C2 forecast is trained on **synthetic sample data**, and the soil moisture output is an **index**, not calibrated VWC.
- All assets are newly authored vector illustrations/icons; no photos, copied artwork, brand trademarks, or externally hosted files are included.
- SVGs are scalable and preserve transparent backgrounds where relevant. PNGs provide convenient fallbacks. Prefer SVG for production web interfaces.

## Examples

```jsx
const ICON_BASE = '/assets/nai-miris/icons';
const WEATHER_BASE = '/assets/nai-miris/weather/icons';
const currentWeatherIcon = hasVerifiedCondition
  ? `${WEATHER_BASE}/${verifiedCondition}.svg`
  : `${WEATHER_BASE}/no-data.svg`;
```

## File integrity

`docs/asset-manifest.json` lists paths and formats. The archive includes vector sources and raster exports.
