const RECENT_FLOOR_PLAN_ID_KEY = "homeInventory.recentFloorPlanId";
const FLOOR_PLAN_VIEWPORT_KEY_PREFIX = "homeInventory.floorPlanViewport";

export type FloorPlanViewportState = {
  zoom: number;
  pan: {
    x: number;
    y: number;
  };
};

export function readRecentFloorPlanId() {
  if (typeof window === "undefined") {
    return "";
  }

  return window.localStorage.getItem(RECENT_FLOOR_PLAN_ID_KEY) ?? "";
}

export function saveRecentFloorPlanId(floorPlanId: number | string) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(RECENT_FLOOR_PLAN_ID_KEY, String(floorPlanId));
}

export function clearRecentFloorPlanId() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(RECENT_FLOOR_PLAN_ID_KEY);
}

export function readFloorPlanViewport(floorPlanId: number | string): FloorPlanViewportState | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = window.localStorage.getItem(viewportStorageKey(floorPlanId));
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as FloorPlanViewportState;
    if (
      !Number.isFinite(parsed.zoom) ||
      !Number.isFinite(parsed.pan?.x) ||
      !Number.isFinite(parsed.pan?.y)
    ) {
      return null;
    }

    return {
      zoom: Math.min(3, Math.max(0.35, parsed.zoom)),
      pan: {
        x: parsed.pan.x,
        y: parsed.pan.y
      }
    };
  } catch {
    return null;
  }
}

export function saveFloorPlanViewport(
  floorPlanId: number | string,
  viewport: FloorPlanViewportState
) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(viewportStorageKey(floorPlanId), JSON.stringify(viewport));
}

function viewportStorageKey(floorPlanId: number | string) {
  return `${FLOOR_PLAN_VIEWPORT_KEY_PREFIX}.${floorPlanId}`;
}
