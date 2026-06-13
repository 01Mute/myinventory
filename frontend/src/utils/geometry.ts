import type { LocationNode, RectGeometry } from "../types/api";

export function isRectGeometry(value: unknown): value is RectGeometry {
  if (!value || typeof value !== "object") {
    return false;
  }

  const geometry = value as Partial<RectGeometry>;
  return (
    geometry.type === "rect" &&
    typeof geometry.x === "number" &&
    typeof geometry.y === "number" &&
    typeof geometry.width === "number" &&
    typeof geometry.height === "number"
  );
}

export function fallbackRect(index: number): RectGeometry {
  return {
    type: "rect",
    x: 40 + (index % 4) * 190,
    y: 40 + Math.floor(index / 4) * 140,
    width: 160,
    height: 96,
    rotation: 0
  };
}

export function rectForNode(
  node: LocationNode,
  index: number,
  drafts: Record<number, RectGeometry>
) {
  if (drafts[node.id]) {
    return drafts[node.id];
  }
  if (isRectGeometry(node.geometry_json)) {
    return node.geometry_json;
  }
  return fallbackRect(index);
}

export function clampRect(rect: RectGeometry, maxWidth: number, maxHeight: number): RectGeometry {
  const width = Math.max(36, Math.min(rect.width, maxWidth));
  const height = Math.max(28, Math.min(rect.height, maxHeight));
  const x = Math.max(0, Math.min(rect.x, maxWidth - width));
  const y = Math.max(0, Math.min(rect.y, maxHeight - height));

  return {
    ...rect,
    x,
    y,
    width,
    height
  };
}

export function normalizeRect(rect: RectGeometry): RectGeometry {
  return {
    ...rect,
    x: Number.isFinite(rect.x) ? rect.x : 0,
    y: Number.isFinite(rect.y) ? rect.y : 0,
    width: Math.max(36, Number.isFinite(rect.width) ? rect.width : 160),
    height: Math.max(28, Number.isFinite(rect.height) ? rect.height : 96)
  };
}

export function expandedSizeForRect(
  rect: RectGeometry,
  currentWidth: number,
  currentHeight: number,
  margin = 120
) {
  return {
    width: Math.max(currentWidth, Math.ceil(rect.x + rect.width + margin)),
    height: Math.max(currentHeight, Math.ceil(rect.y + rect.height + margin))
  };
}

export function rectContains(outer: RectGeometry, inner: RectGeometry) {
  return (
    inner.x >= outer.x &&
    inner.y >= outer.y &&
    inner.x + inner.width <= outer.x + outer.width &&
    inner.y + inner.height <= outer.y + outer.height
  );
}

export function snapRect(
  rect: RectGeometry,
  targets: RectGeometry[],
  canvasWidth: number,
  canvasHeight: number,
  threshold = 10
) {
  const verticalGuides = new Set([0, canvasWidth]);
  const horizontalGuides = new Set([0, canvasHeight]);

  targets.forEach((target) => {
    verticalGuides.add(target.x);
    verticalGuides.add(target.x + target.width / 2);
    verticalGuides.add(target.x + target.width);
    horizontalGuides.add(target.y);
    horizontalGuides.add(target.y + target.height / 2);
    horizontalGuides.add(target.y + target.height);
  });

  let next = normalizeRect(rect);
  const xPoints = [
    { value: next.x, apply: (guide: number) => ({ ...next, x: guide }) },
    {
      value: next.x + next.width / 2,
      apply: (guide: number) => ({ ...next, x: guide - next.width / 2 })
    },
    {
      value: next.x + next.width,
      apply: (guide: number) => ({ ...next, x: guide - next.width })
    }
  ];
  const yPoints = [
    { value: next.y, apply: (guide: number) => ({ ...next, y: guide }) },
    {
      value: next.y + next.height / 2,
      apply: (guide: number) => ({ ...next, y: guide - next.height / 2 })
    },
    {
      value: next.y + next.height,
      apply: (guide: number) => ({ ...next, y: guide - next.height })
    }
  ];

  for (const point of xPoints) {
    const guide = closestGuide(point.value, [...verticalGuides], threshold);
    if (guide !== null) {
      next = point.apply(guide);
      break;
    }
  }

  for (const point of yPoints) {
    const guide = closestGuide(point.value, [...horizontalGuides], threshold);
    if (guide !== null) {
      next = point.apply(guide);
      break;
    }
  }

  return normalizeRect(next);
}

function closestGuide(value: number, guides: number[], threshold: number) {
  let closest: number | null = null;
  let bestDistance = threshold + 1;

  guides.forEach((guide) => {
    const distance = Math.abs(value - guide);
    if (distance <= threshold && distance < bestDistance) {
      closest = guide;
      bestDistance = distance;
    }
  });

  return closest;
}
