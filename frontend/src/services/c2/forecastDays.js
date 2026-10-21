/** Display-only calendar selection. Retains backend row objects and original values. */
export const FORECAST_TIMEZONE = "Asia/Colombo";
const dateParts = new Intl.DateTimeFormat("en-GB", { timeZone: FORECAST_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit" });
const weekday = new Intl.DateTimeFormat("en-GB", { timeZone: FORECAST_TIMEZONE, weekday: "long" });
const dateLabel = new Intl.DateTimeFormat("en-GB", { timeZone: FORECAST_TIMEZONE, day: "2-digit", month: "short", year: "numeric" });
const axisDate = new Intl.DateTimeFormat("en-GB", { timeZone: FORECAST_TIMEZONE, weekday: "short", day: "2-digit", month: "short" });
const clock = new Intl.DateTimeFormat("en-GB", { timeZone: FORECAST_TIMEZONE, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

function timestamp(value) {
  // Backend timestamps must carry an explicit offset; never interpret browser-local dates.
  if (typeof value !== "string" || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) || !Number.isFinite(Date.parse(value))) throw new RangeError("Forecast timestamp requires a valid timezone offset");
  return new Date(value);
}

export function forecastDateKey(value) {
  const parts = Object.fromEntries(dateParts.formatToParts(timestamp(value)).map(({ type, value: part }) => [type, part]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function formatForecastTimestamp(value) {
  const time = timestamp(value);
  return `${weekday.format(time)}, ${dateLabel.format(time)} · ${clock.format(time)}`;
}

export function forecastAxisLabel(value) {
  const time = timestamp(value);
  return { date: axisDate.format(time), time: clock.format(time) };
}

export function groupForecastDays(predictions, horizon) {
  if (![24, 72, 168].includes(horizon)) throw new RangeError("Unsupported forecast horizon");
  const groups = new Map();
  for (const row of predictions.slice(0, horizon)) {
    const key = forecastDateKey(row.timestamp);
    if (!groups.has(key)) {
      const time = timestamp(row.timestamp);
      groups.set(key, { key, weekday: weekday.format(time), date: dateLabel.format(time), rows: [] });
    }
    groups.get(key).rows.push(row);
  }
  return [...groups.values()].map((group) => ({ ...group, count: group.rows.length, partial: group.rows.length < 24, start: group.rows[0].timestamp, end: group.rows.at(-1).timestamp }));
}

export function selectForecastDay(predictions, horizon, dayKey = null) {
  const rows = predictions.slice(0, horizon);
  return dayKey ? rows.filter((row) => forecastDateKey(row.timestamp) === dayKey) : rows;
}
