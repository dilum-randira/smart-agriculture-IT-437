export function farmSummary(farms) {
  const sites = farms.flatMap((farm) => farm.sites);
  const nodes = sites.flatMap((site) => site.nodes);
  return { farms: farms.length, sites: sites.length, nodes: nodes.length, sampleNodes: nodes.filter((node) => node.is_demo && node.source === "synthetic_2025_two_nodes").length };
}
