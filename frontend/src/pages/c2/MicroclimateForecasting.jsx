import { useEffect, useMemo, useRef, useState } from "react";
import { useFarmAccess } from "../../components/c2/microclimate/FarmAccess";
import MicroclimateDashboardView from "../../components/c2/microclimate/MicroclimateDashboardView";
import { accessApi, selectionQuery } from "../../services/c2/accessApi";
import { groupForecastDays } from "../../services/c2/forecastDays";
import { historicalSeries, MODELS, validateForecast } from "../../services/c2/microclimateApi";

import { loadFarmWorkspace } from "../../services/c2/farmSelection";

const EMPTY = [];

export default function MicroclimateForecasting() {
  const access = useFarmAccess();
  const node = access.selection.nodeId;
  const setNode = access.chooseNode;
  const farmId = access.selection.farmId, siteId = access.selection.siteId;
  const farmMode = access.mode === "farm";
  const awaitingSelection = (!farmId || !siteId || !node) && access.accessBusy;
  const [saved, setSaved] = useState([]);
  const [model, setModel] = useState("attention_bilstm");
  const [horizon, setHorizon] = useState(24);
  const [daySelection, setDaySelection] = useState(null);
  const [demo, setDemo] = useState(null);
  const [result, setResult] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [busy, setBusy] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const pending = useRef(null);
  const history = useMemo(() => historicalSeries(demo?.request.observations || EMPTY), [demo]);

  useEffect(() => {
    const controller = new AbortController();
    pending.current?.abort();
    setBusy(""); setDemo(null); setResult(null); setComparison(null); setError(""); setLoadingHistory(true);
    setSaved([]);
    if (farmMode && (!farmId || !siteId || !node)) {
      setLoadingHistory(awaitingSelection); // Selection/loading is an empty state, not a failed forecast.
      return () => controller.abort();
    }
    const request = loadFarmWorkspace(accessApi, farmId, selectionQuery(siteId, node), controller.signal);
    request.then(({ history: data, saved: forecasts, warning }) => { if (!controller.signal.aborted) { setDemo(data); setSaved(forecasts); setError(warning); } })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoadingHistory(false); });
    return () => controller.abort();
  }, [node, retry, farmMode, farmId, siteId, awaitingSelection]);
  useEffect(() => () => pending.current?.abort(), []);

  function selectNode(value) {
    if (value === node || !access.allowedNodes.includes(value)) return;
    pending.current?.abort(); setBusy(""); setNode(value);
  }
  function selectModel(value) {
    pending.current?.abort(); setBusy(""); setModel(value); setResult(null); setError("");
  }
  async function predict(compare = false) {
    if (!demo || loadingHistory) return;
    pending.current?.abort();
    const controller = new AbortController(); pending.current = controller;
    setBusy(compare ? "compare" : "forecast"); setError("");
    const selected = async (id) => {
      const data = await accessApi(`/farms/${farmId}/forecast`, { method: "POST", signal: controller.signal, body: { site_id: siteId, node_id: node, model: id } });
      return validateForecast(data.response, { ...demo.request, model: id });
    };
    try {
      if (compare) {
        const all = await Promise.all(MODELS.map((item) => selected(item.id)));
        if (!controller.signal.aborted) { setComparison(all); setResult(all.find((item) => item.model === model)); }
      } else {
        const forecast = await selected(model);
        if (!controller.signal.aborted) setResult(forecast);
      }
      if (farmMode && !controller.signal.aborted) setSaved(await accessApi(`/farms/${farmId}/forecasts?${selectionQuery(siteId, node)}`, { signal: controller.signal }));
    } catch (err) { if (!controller.signal.aborted) { setError(err.message); controller.abort(); } }
    finally { if (pending.current === controller) { setBusy(""); pending.current = null; } }
  }
  const predictions = result?.predictions || EMPTY;
  const days = useMemo(() => groupForecastDays(predictions, horizon), [predictions, horizon]);
  // A new forecast, saved result or horizon always starts in All Days.
  const selectedDay = daySelection?.predictions === predictions && daySelection.horizon === horizon ? daySelection.key : null;
  const selectedGroup = days.find((day) => day.key === selectedDay);
  const visiblePredictions = selectedGroup?.rows || predictions.slice(0, horizon);
  const ready = !!demo && !loadingHistory;

  function selectSaved(value) {
    const item = saved.find((forecast) => forecast.forecast_id === value);
    if (item) { setResult(item.response); setModel(item.response.model); setComparison(null); }
  }
  return <MicroclimateDashboardView access={access} node={node} model={model} horizon={horizon} saved={saved} demo={demo} result={result} comparison={comparison} busy={busy} loadingHistory={loadingHistory} error={error} ready={ready} history={history} predictions={predictions} days={days} selectedDay={selectedDay} selectedGroup={selectedGroup} visiblePredictions={visiblePredictions} onModel={selectModel} onHorizon={setHorizon} onNode={selectNode} onPredict={predict} onRetry={() => { if (!farmId) access.refreshFarms(); else setRetry((value) => value + 1); }} onSaved={selectSaved} onDay={(key) => setDaySelection(key ? { key, predictions, horizon } : null)} />;
}
