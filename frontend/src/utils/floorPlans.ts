import type { FloorPlan, Home } from "../types/api";

export function nextFloorPlanName(home: Home, floorPlans: FloorPlan[]) {
  const plansForHome = floorPlans.filter((floorPlan) => floorPlan.home === home.id);

  if (plansForHome.length === 0) {
    return home.name;
  }

  let nextFloor = plansForHome.length + 1;
  let name = `${home.name} ${nextFloor}층`;
  const existingNames = new Set(plansForHome.map((floorPlan) => floorPlan.name));

  while (existingNames.has(name)) {
    nextFloor += 1;
    name = `${home.name} ${nextFloor}층`;
  }

  return name;
}
