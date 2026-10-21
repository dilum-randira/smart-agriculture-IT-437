// Select only server-authorized assignments; never synthesize nodes or permissions.
export function firstFarmSelection(farm) {
  const site = farm?.sites?.find((item) => item.nodes?.length) || farm?.sites?.[0];
  return { farmId: farm?.farm_id || "", siteId: site?.site_id || "", nodeId: site?.nodes?.[0]?.node_id || "" };
}

export function assignedFarmSelection(data, previous = {}) {
  const farms = data.filter((item) => item.assigned);
  const previousFarm = farms.find((item) => item.farm_id === previous.farmId);
  const previousSite = previousFarm?.sites?.find((item) => item.site_id === previous.siteId);
  if (previousSite?.nodes?.some((item) => item.node_id === previous.nodeId)) return { farms, selection: previous };
  const farm = previousFarm || farms.find((item) => item.sites?.some((site) => site.nodes?.length)) || farms[0];
  return { farms, selection: firstFarmSelection(farm) };
}

// Saved-result availability must never determine whether genuine history is usable.
export async function loadFarmWorkspace(api, farmId, query, signal) {
  const [history, saved] = await Promise.allSettled([
    api(`/farms/${farmId}/history?${query}`, { signal }),
    api(`/farms/${farmId}/forecasts?${query}`, { signal }),
  ]);
  if (history.status === "rejected") throw history.reason;
  return { history: history.value, saved: saved.status === "fulfilled" ? saved.value : [], warning: saved.status === "rejected" ? `History is ready, but saved forecasts could not be loaded: ${saved.reason.message}` : "" };
}
