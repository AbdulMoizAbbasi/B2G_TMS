import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { LogOut } from "lucide-react";
import {
  LayoutDashboard,
  ClipboardList,
  FileSearch,
  TrendingUp,
  Sun,
  Moon,
} from "lucide-react";

function Layout() {
  const { user, logout } = useAuth();
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem("theme") === "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute(
      "data-theme",
      darkMode ? "dark" : "light"
    );

    localStorage.setItem(
      "theme",
      darkMode ? "dark" : "light"
    );
  }, [darkMode]);

  const navItems = [
    {
      label: "All Tenders",
      path: "/",
      icon: ClipboardList,
    },
    {
      label: "Participated Tenders",
      path: "/participated",
      icon: LayoutDashboard,
    },
    {
      label: "Evaluation Reports",
      path: "/evaluations",
      icon: FileSearch,
    },
    {
      label: "Project Updates",
      path: "/project-updates",
      icon: TrendingUp,
    },
  ];

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>JazzWorld</h1>
          <span>B2G Tender Portal</span>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  `nav-item ${isActive ? "active" : ""}`
                }
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-name">
              {user?.name || user?.username}
            </div>

            <div className="user-role">
              {user?.role}
            </div>
          </div>

          <button
            className="logout-button"
            onClick={logout}
            title="Logout"
          >
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <main className="main-content">
        <div className="top-bar">
          <div />

          <button
            className="theme-toggle"
            onClick={() => setDarkMode((current) => !current)}
            aria-label="Toggle theme"
            title={
              darkMode
                ? "Switch to light mode"
                : "Switch to dark mode"
            }
          >
            {darkMode ? (
              <Sun size={19} />
            ) : (
              <Moon size={19} />
            )}
          </button>
        </div>

        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

export default Layout;