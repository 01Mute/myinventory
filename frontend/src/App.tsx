import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import type { ReactElement } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "./api/client";
import { AppShell } from "./components/AppShell";
import { useAuth } from "./context/AuthContext";
import { AuthPage } from "./pages/AuthPage";
import { FloorPlanEditorPage } from "./pages/FloorPlanEditorPage";
import { HomesPage } from "./pages/HomesPage";
import { ItemsPage } from "./pages/ItemsPage";
import { LocationsPage } from "./pages/LocationsPage";
import type { FloorPlan, Home } from "./types/api";

export function App() {
  const { loading } = useAuth();

  if (loading) {
    return <div className="screen-loader">Loading</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<PublicOnly element={<AuthPage mode="login" />} />} />
      <Route path="/register" element={<PublicOnly element={<AuthPage mode="register" />} />} />
      <Route path="/forgot-password" element={<PublicOnly element={<AuthPage mode="reset" />} />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<StartPage />} />
          <Route path="/homes" element={<HomesPage />} />
          <Route path="/locations" element={<LocationsPage />} />
          <Route path="/editor" element={<FloorPlanEditorPage />} />
          <Route path="/floor-plans/:floorPlanId/editor" element={<FloorPlanEditorPage />} />
          <Route path="/items" element={<ItemsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function RequireAuth() {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

function PublicOnly({ element }: { element: ReactElement }) {
  const { user } = useAuth();
  if (user) {
    return <Navigate to="/" replace />;
  }
  return element;
}

function StartPage() {
  const homesQuery = useQuery({ queryKey: ["homes"], queryFn: () => api.get<Home[]>("/homes/") });
  const floorPlansQuery = useQuery({
    queryKey: ["floor-plans"],
    queryFn: () => api.get<FloorPlan[]>("/floor-plans/")
  });

  if (homesQuery.isLoading || floorPlansQuery.isLoading) {
    return <div className="screen-loader">Loading</div>;
  }

  if ((homesQuery.data ?? []).length === 0 || (floorPlansQuery.data ?? []).length === 0) {
    return <Navigate to="/homes" replace />;
  }

  return <Navigate to="/items" replace />;
}
