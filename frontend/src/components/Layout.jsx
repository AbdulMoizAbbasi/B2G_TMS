import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { LogOut, Menu, X } from "lucide-react";
import { ClipboardList, LayoutDashboard, Sun, Moon } from "lucide-react";
import jazzRadarLogo from "../assets/logo.png";

function Layout() {
  const { user, logout } = useAuth();
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem("theme") === "dark";
  });
  const [sidebarOpen, setSidebarOpen] = useState(true);

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
      label: "Overview",
      path: "/overview",
      icon: LayoutDashboard,
    },
    {
      label: "All Tenders",
      path: "/",
      icon: ClipboardList,
    },
  ];

  return (
    <div className={`app-layout ${sidebarOpen ? "" : "sidebar-is-hidden"}`}>
      <aside className="sidebar" aria-hidden={!sidebarOpen} inert={!sidebarOpen}>
        <div className="sidebar-header">
          <img className="sidebar-brand-logo" src={jazzRadarLogo} alt="Jazz Radar logo" />
          <h1>Jazz Radar</h1>
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
          <button
            className="sidebar-toggle"
            type="button"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-label={sidebarOpen ? "Hide navigation menu" : "Show navigation menu"}
            aria-expanded={sidebarOpen}
            title={sidebarOpen ? "Hide menu" : "Show menu"}
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

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
