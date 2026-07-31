import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Home as HomeIcon, Layers, Plus, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { IconButton } from "../components/IconButton";
import type { FloorPlan, Home } from "../types/api";
import { nextFloorPlanName } from "../utils/floorPlans";
import {
  clearRecentFloorPlanId,
  readRecentFloorPlanId,
  saveRecentFloorPlanId
} from "../utils/recentFloorPlan";

export function HomesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const homesQuery = useQuery({ queryKey: ["homes"], queryFn: () => api.getAll<Home>("/homes/") });
  const floorPlansQuery = useQuery({
    queryKey: ["floor-plans"],
    queryFn: () => api.getAll<FloorPlan>("/floor-plans/")
  });

  const homes = homesQuery.data ?? [];
  const floorPlans = floorPlansQuery.data ?? [];
  const [homeForm, setHomeForm] = useState({ name: "", address_optional: "" });
  const [selectedHomeId, setSelectedHomeId] = useState("");
  const [selectedFloorPlanId, setSelectedFloorPlanId] = useState(() => readRecentFloorPlanId());

  useEffect(() => {
    if (selectedHomeId || homes.length === 0 || floorPlansQuery.isLoading) {
      return;
    }

    const recentFloorPlan = floorPlans.find(
      (floorPlan) => String(floorPlan.id) === selectedFloorPlanId
    );
    setSelectedHomeId(String(recentFloorPlan?.home ?? homes[0].id));
  }, [floorPlans, floorPlansQuery.isLoading, homes, selectedFloorPlanId, selectedHomeId]);

  const selectedHome = useMemo(
    () => homes.find((home) => String(home.id) === selectedHomeId) ?? null,
    [homes, selectedHomeId]
  );
  const selectedHomeFloorPlans = useMemo(
    () => floorPlans.filter((floorPlan) => String(floorPlan.home) === selectedHomeId),
    [floorPlans, selectedHomeId]
  );

  useEffect(() => {
    if (!floorPlansQuery.isSuccess || !selectedFloorPlanId) {
      return;
    }
    if (floorPlans.some((floorPlan) => String(floorPlan.id) === selectedFloorPlanId)) {
      return;
    }

    setSelectedFloorPlanId("");
    clearRecentFloorPlanId();
  }, [floorPlans, floorPlansQuery.isSuccess, selectedFloorPlanId]);

  const createHome = useMutation({
    mutationFn: async (payload: typeof homeForm) => {
      const home = await api.post<Home>("/homes/", payload);
      const floorPlan = await api.post<FloorPlan>("/floor-plans/", {
        home: home.id,
        name: nextFloorPlanName(home, [])
      });
      return { home, floorPlan };
    },
    onSuccess: async ({ home, floorPlan }) => {
      setHomeForm({ name: "", address_optional: "" });
      setSelectedHomeId(String(home.id));
      setSelectedFloorPlanId(String(floorPlan.id));
      saveRecentFloorPlanId(floorPlan.id);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["homes"] }),
        queryClient.invalidateQueries({ queryKey: ["floor-plans"] })
      ]);
      navigate(`/floor-plans/${floorPlan.id}/editor`);
    }
  });

  const createFloorPlan = useMutation({
    mutationFn: async () => {
      if (!selectedHome) {
        throw new Error("집을 먼저 선택하세요.");
      }

      return api.post<FloorPlan>("/floor-plans/", {
        home: selectedHome.id,
        name: nextFloorPlanName(selectedHome, floorPlans)
      });
    },
    onSuccess: (floorPlan) => {
      setSelectedFloorPlanId(String(floorPlan.id));
      saveRecentFloorPlanId(floorPlan.id);
      queryClient.invalidateQueries({ queryKey: ["floor-plans"] });
      navigate(`/floor-plans/${floorPlan.id}/editor`);
    }
  });

  const deleteFloorPlan = useMutation({
    mutationFn: (floorPlan: FloorPlan) => api.delete<null>(`/floor-plans/${floorPlan.id}/`),
    onSuccess: (_data, deletedFloorPlan) => {
      if (selectedFloorPlanId === String(deletedFloorPlan.id)) {
        const nextFloorPlan =
          floorPlans.find(
            (floorPlan) => floorPlan.id !== deletedFloorPlan.id && floorPlan.home === deletedFloorPlan.home
          ) ?? floorPlans.find((floorPlan) => floorPlan.id !== deletedFloorPlan.id);

        if (nextFloorPlan) {
          setSelectedHomeId(String(nextFloorPlan.home));
          setSelectedFloorPlanId(String(nextFloorPlan.id));
          saveRecentFloorPlanId(nextFloorPlan.id);
        } else {
          setSelectedFloorPlanId("");
          clearRecentFloorPlanId();
        }
      }
      queryClient.invalidateQueries({ queryKey: ["floor-plans"] });
      queryClient.invalidateQueries({ queryKey: ["location-nodes"] });
    }
  });

  function submitHome(event: FormEvent) {
    event.preventDefault();
    createHome.mutate(homeForm);
  }

  function submitFloorPlan(event: FormEvent) {
    event.preventDefault();
    createFloorPlan.mutate();
  }

  function confirmDeleteFloorPlan(floorPlan: FloorPlan) {
    if (window.confirm(`정말 "${floorPlan.name}" 도면을 삭제하시겠습니까?`)) {
      deleteFloorPlan.mutate(floorPlan);
    }
  }

  function openFloorPlan(floorPlan: FloorPlan) {
    setSelectedFloorPlanId(String(floorPlan.id));
    saveRecentFloorPlanId(floorPlan.id);
    navigate(`/floor-plans/${floorPlan.id}/editor`);
  }

  function selectHome(home: Home) {
    setSelectedHomeId(String(home.id));
    const recentFloorPlan = floorPlans.find(
      (floorPlan) =>
        floorPlan.home === home.id && String(floorPlan.id) === readRecentFloorPlanId()
    );
    const firstFloorPlan = floorPlans.find((floorPlan) => floorPlan.home === home.id);
    setSelectedFloorPlanId(
      recentFloorPlan ? String(recentFloorPlan.id) : firstFloorPlan ? String(firstFloorPlan.id) : ""
    );
  }

  function handleHomeKeyDown(event: KeyboardEvent<HTMLElement>, home: Home) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectHome(home);
    }
  }

  function handleFloorPlanKeyDown(event: KeyboardEvent<HTMLElement>, floorPlan: FloorPlan) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openFloorPlan(floorPlan);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <h1>집/도면</h1>
        </div>
      </header>

      <div className="grid two-columns">
        <section className="panel">
          <div className="panel-header">
            <h2>
              <HomeIcon aria-hidden="true" />
              집
            </h2>
          </div>
          <ErrorBanner error={homesQuery.error || createHome.error} />
          <form className="form-grid" onSubmit={submitHome}>
            <label>
              이름
              <input
                value={homeForm.name}
                onChange={(event) => setHomeForm({ ...homeForm, name: event.target.value })}
                required
              />
            </label>
            <label>
              주소
              <input
                value={homeForm.address_optional}
                onChange={(event) =>
                  setHomeForm({ ...homeForm, address_optional: event.target.value })
                }
              />
            </label>
            <IconButton icon={Plus} label="집 추가" disabled={createHome.isPending} type="submit" />
          </form>

          <div className="list-panel">
            {homes.length === 0 ? (
              <EmptyState title="등록된 집이 없습니다." />
            ) : (
              homes.map((home) => (
                <article
                  className={`row-card clickable ${selectedHomeId === String(home.id) ? "selected" : ""}`}
                  key={home.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => selectHome(home)}
                  onKeyDown={(event) => handleHomeKeyDown(event, home)}
                >
                  <div>
                    <strong>{home.name}</strong>
                    <span>{home.address_optional || "주소 없음"}</span>
                  </div>
                  <span className="count-pill">
                    {floorPlans.filter((floorPlan) => floorPlan.home === home.id).length} 도면
                  </span>
                </article>
              ))
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>
              <Layers aria-hidden="true" />
              도면
            </h2>
          </div>
          <ErrorBanner error={floorPlansQuery.error || createFloorPlan.error || deleteFloorPlan.error} />
          <form className="form-grid compact-form" onSubmit={submitFloorPlan}>
            <label>
              집
              <select
                value={selectedHomeId}
                onChange={(event) => {
                  const nextHomeId = event.target.value;
                  const recentFloorPlan = floorPlans.find(
                    (floorPlan) =>
                      String(floorPlan.home) === nextHomeId &&
                      String(floorPlan.id) === readRecentFloorPlanId()
                  );
                  const firstFloorPlan = floorPlans.find(
                    (floorPlan) => String(floorPlan.home) === nextHomeId
                  );

                  setSelectedHomeId(nextHomeId);
                  setSelectedFloorPlanId(
                    recentFloorPlan
                      ? String(recentFloorPlan.id)
                      : firstFloorPlan
                        ? String(firstFloorPlan.id)
                        : ""
                  );
                }}
                required
              >
                <option value="">선택</option>
                {homes.map((home) => (
                  <option key={home.id} value={home.id}>
                    {home.name}
                  </option>
                ))}
              </select>
            </label>
            <IconButton
              icon={Plus}
              label={selectedHomeFloorPlans.length === 0 ? "기본 도면 만들기" : "층/도면 추가"}
              disabled={createFloorPlan.isPending || !selectedHome}
              type="submit"
            />
          </form>

          <div className="list-panel">
            {!selectedHome ? (
              <EmptyState title="집을 선택하세요." />
            ) : selectedHomeFloorPlans.length === 0 ? (
              <EmptyState title="선택된 집의 도면이 없습니다." />
            ) : (
              selectedHomeFloorPlans.map((floorPlan) => (
                <article
                  className={`row-card clickable ${
                    selectedFloorPlanId === String(floorPlan.id) ? "selected" : ""
                  }`}
                  key={floorPlan.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => openFloorPlan(floorPlan)}
                  onKeyDown={(event) => handleFloorPlanKeyDown(event, floorPlan)}
                >
                  <div>
                    <strong>{floorPlan.name}</strong>
                    <span>{floorPlan.home_name}</span>
                  </div>
                  <div className="row-actions vertical">
                    <Link
                      className="icon-link"
                      to={`/floor-plans/${floorPlan.id}/editor`}
                      title="도면 편집"
                      onClick={(event) => {
                        event.stopPropagation();
                        setSelectedFloorPlanId(String(floorPlan.id));
                        saveRecentFloorPlanId(floorPlan.id);
                      }}
                      onKeyDown={(event) => event.stopPropagation()}
                    >
                      <Layers aria-hidden="true" />
                      <span>편집</span>
                    </Link>
                    <button
                      className="icon-link danger-link"
                      type="button"
                      title="도면 삭제"
                      disabled={deleteFloorPlan.isPending}
                      onKeyDown={(event) => event.stopPropagation()}
                      onClick={(event) => {
                        event.stopPropagation();
                        confirmDeleteFloorPlan(floorPlan);
                      }}
                    >
                      <Trash2 aria-hidden="true" />
                      <span>도면삭제</span>
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      </div>
    </section>
  );
}
