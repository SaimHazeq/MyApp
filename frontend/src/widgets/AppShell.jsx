import { NavLink, useNavigate } from "react-router-dom";
import { Clapperboard, Home, PlusCircle, Film, Settings as SettingsIcon, LogOut, Sun, Moon } from "lucide-react";
import { useAuth } from "../state/AuthContext";
import { useTheme } from "../theme/ThemeProvider";

const NAV_ITEMS = [
  { to: "/home", icon: Home, label: "Home" },
  { to: "/create", icon: PlusCircle, label: "Create Movie" },
  { to: "/movies", icon: Film, label: "My Movies" },
  { to: "/settings", icon: SettingsIcon, label: "Settings" },
];

export function AppShell({ title, subtitle, actions, children }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex">
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-studio-border bg-studio-surface/60 px-4 py-6">
        <div className="flex items-center gap-2 px-2 mb-8">
          <div className="w-9 h-9 rounded-xl bg-marquee flex items-center justify-center">
            <Clapperboard size={18} className="text-studio-bg" />
          </div>
          <div className="font-display font-bold text-lg leading-tight">Cartoon<br />Movie Maker</div>
        </div>

        <nav className="flex-1 space-y-1">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-marquee/15 text-marquee"
                    : "text-studio-muted hover:text-studio-text hover:bg-studio-surface2"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-1 pt-4 border-t border-studio-border">
          <button
            onClick={toggleTheme}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-studio-muted hover:text-studio-text hover:bg-studio-surface2 transition-colors"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-studio-muted hover:text-danger hover:bg-danger/10 transition-colors"
          >
            <LogOut size={18} />
            Log out
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between gap-4 px-6 md:px-10 py-6 border-b border-studio-border">
          <div>
            {subtitle && <p className="label-eyebrow mb-1">{subtitle}</p>}
            <h1 className="font-display text-2xl font-bold">{title}</h1>
          </div>
          <div className="flex items-center gap-3">
            {actions}
            <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-studio-border">
              <div className="w-8 h-8 rounded-full bg-reel/20 text-reel flex items-center justify-center text-sm font-semibold">
                {user?.full_name?.[0]?.toUpperCase() || "?"}
              </div>
              <span className="text-sm text-studio-muted">{user?.full_name}</span>
            </div>
          </div>
        </header>

        <main className="flex-1 px-6 md:px-10 py-8 overflow-y-auto">{children}</main>

        {/* Mobile bottom nav */}
        <nav className="md:hidden fixed bottom-0 inset-x-0 bg-studio-surface border-t border-studio-border flex justify-around py-2">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `flex flex-col items-center gap-0.5 px-3 py-1 text-[11px] ${isActive ? "text-marquee" : "text-studio-muted"}`}
            >
              <Icon size={20} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
