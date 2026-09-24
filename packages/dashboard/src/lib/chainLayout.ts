import { Graph, layout } from "@dagrejs/dagre";

export const SURFACE_NODE_WIDTH = 248;
export const SURFACE_NODE_HEIGHT = 124;

export function layoutSurface(
  nodeIds: string[],
  edges: Array<{ source: string; target: string }>,
): Map<string, { x: number; y: number }> {
  const graph = new Graph({ directed: true });
  graph.setGraph({
    rankdir: "LR",
    nodesep: 40,
    ranksep: 88,
    edgesep: 24,
    marginx: 16,
    marginy: 16,
  });
  graph.setDefaultEdgeLabel(() => ({}));

  for (const id of nodeIds) {
    graph.setNode(id, { width: SURFACE_NODE_WIDTH, height: SURFACE_NODE_HEIGHT });
  }

  const known = new Set(nodeIds);
  for (const edge of edges) {
    if (known.has(edge.source) && known.has(edge.target)) {
      graph.setEdge(edge.source, edge.target);
    }
  }

  layout(graph);

  const positions = new Map<string, { x: number; y: number }>();
  for (const id of nodeIds) {
    const placed = graph.node(id);
    positions.set(id, {
      x: (placed?.x ?? 0) - SURFACE_NODE_WIDTH / 2,
      y: (placed?.y ?? 0) - SURFACE_NODE_HEIGHT / 2,
    });
  }
  return positions;
}
