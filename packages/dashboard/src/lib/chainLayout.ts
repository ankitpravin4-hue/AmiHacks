import { Graph, layout } from "@dagrejs/dagre";

export const SURFACE_NODE_WIDTH = 248;
export const SURFACE_NODE_HEIGHT = 124;
export const SURFACE_RANKSEP = 120;
export const SURFACE_NODESEP = 60;
export const STANDALONE_GROUP_ID = "standalone-group";

export interface SurfaceGroupBox {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface FindingPosition {
  x: number;
  y: number;
  parentNode?: string;
}

function rankSeparation(canvasWidth: number, maxRanks: number): number {
  if (canvasWidth < 480 || maxRanks <= 1) return SURFACE_RANKSEP;
  const targetWidth = canvasWidth * 0.8;
  const next = (targetWidth - maxRanks * SURFACE_NODE_WIDTH) / (maxRanks - 1);
  return Math.max(SURFACE_RANKSEP, next);
}

function layoutChainRow(
  findingIds: string[],
  ranksep: number,
): Map<string, { x: number; y: number }> {
  const graph = new Graph({ directed: true });
  graph.setGraph({
    rankdir: "LR",
    nodesep: SURFACE_NODESEP,
    ranksep,
    edgesep: 24,
    marginx: 0,
    marginy: 0,
  });
  graph.setDefaultEdgeLabel(() => ({}));

  for (const id of findingIds) {
    graph.setNode(id, { width: SURFACE_NODE_WIDTH, height: SURFACE_NODE_HEIGHT });
  }
  for (let index = 1; index < findingIds.length; index += 1) {
    graph.setEdge(findingIds[index - 1], findingIds[index]);
  }
  layout(graph);

  const raw = new Map<string, { x: number; y: number }>();
  let minX = Infinity;
  let minY = Infinity;
  for (const id of findingIds) {
    const placed = graph.node(id);
    const x = (placed?.x ?? 0) - SURFACE_NODE_WIDTH / 2;
    const y = (placed?.y ?? 0) - SURFACE_NODE_HEIGHT / 2;
    raw.set(id, { x, y });
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
  }
  if (!Number.isFinite(minX)) {
    minX = 0;
    minY = 0;
  }

  const normalized = new Map<string, { x: number; y: number }>();
  for (const id of findingIds) {
    const point = raw.get(id) ?? { x: 0, y: 0 };
    normalized.set(id, { x: point.x - minX, y: point.y - minY });
  }
  return normalized;
}

function rowBounds(ids: string[], positions: Map<string, { x: number; y: number }>) {
  let maxX = 0;
  let maxY = 0;
  for (const id of ids) {
    const point = positions.get(id);
    if (!point) continue;
    maxX = Math.max(maxX, point.x + SURFACE_NODE_WIDTH);
    maxY = Math.max(maxY, point.y + SURFACE_NODE_HEIGHT);
  }
  return { width: maxX, height: maxY };
}

export function layoutSurface(
  findingIds: string[],
  chains: Array<{ finding_ids: string[] }>,
  canvasWidth = 0,
): { positions: Map<string, FindingPosition>; group: SurfaceGroupBox | null } {
  const known = new Set(findingIds);
  const chained = new Set<string>();
  const positions = new Map<string, FindingPosition>();
  let cursorY = 0;
  let mapWidth = 0;
  const maxRanks = Math.max(1, ...chains.map((chain) => chain.finding_ids.length), 2);
  const ranksep = rankSeparation(canvasWidth, maxRanks);

  for (const chain of chains) {
    const rowIds = chain.finding_ids.filter((id) => known.has(id));
    if (rowIds.length === 0) continue;
    const row = layoutChainRow(rowIds, ranksep);
    for (const id of rowIds) {
      const point = row.get(id) ?? { x: 0, y: 0 };
      positions.set(id, { x: point.x, y: cursorY + point.y });
      chained.add(id);
    }
    const bounds = rowBounds(rowIds, row);
    mapWidth = Math.max(mapWidth, bounds.width);
    cursorY += bounds.height + SURFACE_NODESEP;
  }

  const standalone = findingIds.filter((id) => !chained.has(id));
  if (standalone.length === 0) {
    return { positions, group: null };
  }

  const labelHeight = 24;
  const padX = 20;
  const padTop = 6;
  const padBottom = 12;
  const innerWidth =
    standalone.length * SURFACE_NODE_WIDTH + Math.max(0, standalone.length - 1) * SURFACE_NODESEP;
  const groupWidth = Math.max(innerWidth + padX * 2, mapWidth);
  const groupHeight = labelHeight + padTop + SURFACE_NODE_HEIGHT + padBottom;
  const startX = padX + Math.max(0, (groupWidth - padX * 2 - innerWidth) / 2);

  standalone.forEach((id, index) => {
    positions.set(id, {
      x: startX + index * (SURFACE_NODE_WIDTH + SURFACE_NODESEP),
      y: labelHeight + padTop,
      parentNode: STANDALONE_GROUP_ID,
    });
  });

  return {
    positions,
    group: {
      id: STANDALONE_GROUP_ID,
      x: 0,
      y: cursorY,
      width: groupWidth,
      height: groupHeight,
    },
  };
}
