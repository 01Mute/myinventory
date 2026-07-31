import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MapPinned } from "lucide-react";

import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { LocationPicker } from "../components/LocationPicker";
import type { FloorPlan, Home, Item, LocationNode } from "../types/api";
import { buildLocationTree } from "../utils/tree";
import { toggleSetValue } from "../utils/sets";

export function LocationsPage() {
  const homesQuery = useQuery({ queryKey: ["homes"], queryFn: () => api.getAll<Home>("/homes/") });
  const floorPlansQuery = useQuery({
    queryKey: ["floor-plans"],
    queryFn: () => api.getAll<FloorPlan>("/floor-plans/")
  });
  const locationsQuery = useQuery({
    queryKey: ["location-nodes"],
    queryFn: () => api.getAll<LocationNode>("/location-nodes/")
  });

  const homes = homesQuery.data ?? [];
  const floorPlans = floorPlansQuery.data ?? [];
  const allLocations = locationsQuery.data ?? [];
  const [selectedHomeId, setSelectedHomeId] = useState("");
  const [selectedFloorPlanId, setSelectedFloorPlanId] = useState("");
  const [selectedLocationId, setSelectedLocationId] = useState("");
  const [expandedLocationIds, setExpandedLocationIds] = useState<Set<number>>(() => new Set());

  useEffect(() => {
    if (!selectedHomeId && homes.length > 0) {
      setSelectedHomeId(String(homes[0].id));
    }
  }, [homes, selectedHomeId]);

  const visibleFloorPlans = useMemo(
    () => floorPlans.filter((floorPlan) => String(floorPlan.home) === selectedHomeId),
    [floorPlans, selectedHomeId]
  );

  useEffect(() => {
    if (visibleFloorPlans.length > 0 && !selectedFloorPlanId) {
      setSelectedFloorPlanId(String(visibleFloorPlans[0].id));
    }
    if (visibleFloorPlans.length === 0 && selectedFloorPlanId) {
      setSelectedFloorPlanId("");
      setSelectedLocationId("");
    }
  }, [selectedFloorPlanId, visibleFloorPlans]);

  const floorLocations = useMemo(
    () =>
      allLocations.filter((location) =>
        selectedFloorPlanId ? String(location.floor_plan) === selectedFloorPlanId : false
      ),
    [allLocations, selectedFloorPlanId]
  );
  const tree = useMemo(() => buildLocationTree(floorLocations), [floorLocations]);

  const itemsQuery = useQuery({
    queryKey: ["items", "location-page", selectedLocationId],
    queryFn: () =>
      api.getAll<Item>(`/items/?location_node_id=${selectedLocationId}&include_children=true`),
    enabled: Boolean(selectedLocationId)
  });

  const selectedItems = itemsQuery.data ?? [];

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <h1>위치</h1>
        </div>
      </header>

      <div className="grid location-layout">
        <section className="panel">
          <div className="panel-header">
            <h2>
              <MapPinned aria-hidden="true" />
              위치 조회
            </h2>
          </div>
          <ErrorBanner error={homesQuery.error || floorPlansQuery.error || locationsQuery.error} />
          <div className="form-grid">
            <label>
              집
              <select
                value={selectedHomeId}
                onChange={(event) => {
                  setSelectedHomeId(event.target.value);
                  setSelectedFloorPlanId("");
                  setSelectedLocationId("");
                  setExpandedLocationIds(new Set());
                }}
              >
                <option value="">선택</option>
                {homes.map((home) => (
                  <option key={home.id} value={home.id}>
                    {home.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              도면
              <select
                value={selectedFloorPlanId}
                onChange={(event) => {
                  setSelectedFloorPlanId(event.target.value);
                  setSelectedLocationId("");
                  setExpandedLocationIds(new Set());
                }}
              >
                <option value="">선택</option>
                {visibleFloorPlans.map((floorPlan) => (
                  <option key={floorPlan.id} value={floorPlan.id}>
                    {floorPlan.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="field-block">
              <span className="field-label">위치</span>
              <LocationPicker
                emptyLabel="위치 선택"
                expandedIds={expandedLocationIds}
                selectedId={selectedLocationId}
                tree={tree}
                onSelect={setSelectedLocationId}
                onToggle={(nodeId) =>
                  setExpandedLocationIds((current) => toggleSetValue(current, nodeId))
                }
              />
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>포함된 물건</h2>
            {selectedLocationId ? <span className="count-pill">{selectedItems.length}</span> : null}
          </div>
          <ErrorBanner error={itemsQuery.error} />
          {!selectedLocationId ? (
            <EmptyState title="위치를 선택하세요." />
          ) : selectedItems.length === 0 ? (
            <EmptyState title="포함된 물건이 없습니다." />
          ) : (
            <div className="list-panel included-items-scroll">
              {selectedItems.map((item) => (
                <article className="row-card" key={item.id}>
                  <div>
                    <strong>{item.name}</strong>
                    <span>{item.location_path || item.location_code || "미지정"}</span>
                  </div>
                  <span className="count-pill">{item.quantity}</span>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
