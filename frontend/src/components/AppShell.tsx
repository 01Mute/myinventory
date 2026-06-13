import { Boxes, Home, Layers, LogOut, Map, PackageSearch } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/items", label: "물건", icon: PackageSearch },
  { to: "/editor", label: "도면 편집", icon: Layers },
  { to: "/locations", label: "위치", icon: Map },
  { to: "/homes", label: "집/도면", icon: Home }
];

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Boxes aria-hidden="true" />
          <div>
            <strong>Home Inventory Map</strong>
            <span>{user?.nickname || user?.email}</span>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} className="nav-link">
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <button className="ghost-button sidebar-action" type="button" onClick={logout} title="로그아웃">
          <LogOut aria-hidden="true" />
          <span>로그아웃</span>
        </button>
      </aside>

      <main className="main-panel">
        <Outlet />
      </main>
    </div>
  );
}
