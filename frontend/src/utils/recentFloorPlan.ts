const RECENT_FLOOR_PLAN_ID_KEY = "homeInventory.recentFloorPlanId";

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
