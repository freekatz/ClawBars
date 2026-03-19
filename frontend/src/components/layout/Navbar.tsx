import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  TrendingUp,
  Compass,
  BarChart2,
  GlassWater,
  Plus,
  LogOut,
  Settings,
  Sun,
  Moon,
} from "lucide-react";
import { ROUTES } from "@/config/constants";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { api } from "@/lib/api";

export default function Navbar() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const { data: barsData } = useQuery({
    queryKey: ["navbar-bars", user?.id],
    queryFn: () =>
      api.get<{ data: any }>("/owner/bars").then((res) => res.data || []),
    enabled:
      !!user &&
      (user.role === "owner" ||
        user.role === "premium" ||
        user.role === "admin"),
  });

  const { data: joinedBarsData } = useQuery({
    queryKey: ["joined-bars", user?.id],
    queryFn: () =>
      api.get<{ data: any }>("/bars/joined").then((res) => res.data || []),
    enabled: !!user,
  });

  const bars = Array.isArray(barsData) ? barsData.slice(0, 5) : [];
  const joinedBars = Array.isArray(joinedBarsData)
    ? joinedBarsData.slice(0, 5)
    : [];

  const navItems = [
    {
      to: ROUTES.HOME,
      icon: <Search size={18} />,
      label: t("nav.home"),
      end: true,
    },
    {
      to: ROUTES.TRENDS,
      icon: <TrendingUp size={18} />,
      label: t("nav.trends"),
    },
    { to: ROUTES.BARS, icon: <Compass size={18} />, label: t("nav.discover") },
    { to: ROUTES.STATS, icon: <BarChart2 size={18} />, label: t("nav.stats") },
  ];

  const displayName = user?.name || user?.email?.split("@")[0] || "User";

  return (
    <nav className="flex-1 flex flex-col gap-4">
      <div className="mb-2 px-3 py-3 bg-card border-2 border-black shadow-[2px_2px_0_0_#000] flex items-center justify-between group hover:bg-card-hover transition-all">
        <NavLink
          to={ROUTES.PROFILE}
          className="flex items-center gap-3 flex-1 overflow-hidden"
        >
          <div className="w-9 h-9 flex-shrink-0 bg-primary/20 border-2 border-black flex items-center justify-center text-sm font-black text-primary italic">
            {displayName.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-black font-mono text-foreground uppercase italic tracking-tighter group-hover:text-primary transition-colors truncate">
              {displayName}
            </div>
            <div className="text-[9px] font-mono font-black text-primary flex items-center gap-1 truncate uppercase">
              {user?.role?.toUpperCase()}
            </div>
          </div>
        </NavLink>
        <button
          onClick={logout}
          className="text-muted-foreground hover:text-white p-2 ml-1 border-2 border-black hover:bg-destructive transition-all flex-shrink-0"
          title={t("common.logout")}
          aria-label={t("common.logout")}
        >
          <LogOut size={16} />
        </button>
      </div>

      <div className="space-y-0.5">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={"end" in item ? item.end : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 border-2 transition-all text-sm ${
                isActive
                  ? "bg-black text-white font-black border-black shadow-[2px_2px_0_0_#ff4757] -translate-x-0.5 -translate-y-0.5"
                  : "text-muted-foreground border-transparent hover:text-foreground hover:bg-muted font-bold"
              }`
            }
          >
            {item.icon}
            <span className="uppercase tracking-tight">{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="mt-2">
        <h3 className="px-3 text-xs font-black text-foreground uppercase tracking-widest mb-2 flex justify-between items-center italic">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-primary animate-pulse" />
            {t("nav.my_bars")}
          </span>
          <NavLink
            to={ROUTES.CREATE_BAR}
            className="w-7 h-7 bg-black text-white flex items-center justify-center border-2 border-black hover:bg-primary transition-all shadow-[1px_1px_0_0_#ffa502]"
          >
            <Plus size={14} strokeWidth={3} />
          </NavLink>
        </h3>
        <div className="space-y-0.5">
          {bars.map((bar: any) => (
            <NavLink
              key={bar.id}
              to={ROUTES.BAR_DETAIL(bar.slug)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 border-2 transition-all text-sm ${
                  isActive
                    ? "bg-black text-white font-black border-black shadow-[2px_2px_0_0_#ffa502] -translate-x-0.5 -translate-y-0.5"
                    : "text-muted-foreground border-transparent hover:text-foreground hover:bg-muted font-bold"
                }`
              }
            >
              <GlassWater size={16} />
              <span className="truncate uppercase tracking-tight">
                {bar.name}
              </span>
            </NavLink>
          ))}
        </div>
      </div>

      {joinedBars.length > 0 && (
        <div className="mt-1">
          <h3 className="px-3 text-xs font-black text-foreground uppercase tracking-widest mb-2 flex items-center gap-1.5 italic">
            <span className="w-1.5 h-1.5 bg-accent" />
            {t("nav.joined_bars")}
          </h3>
          <div className="space-y-0.5">
            {joinedBars.map((bar: any) => (
              <NavLink
                key={bar.id}
                to={ROUTES.BAR_DETAIL(bar.slug)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 border-2 transition-all text-sm ${
                    isActive
                      ? "bg-black text-white font-black border-black shadow-[2px_2px_0_0_#ffa502] -translate-x-0.5 -translate-y-0.5"
                      : "text-muted-foreground border-transparent hover:text-foreground hover:bg-muted font-bold"
                  }`
                }
              >
                <GlassWater size={16} />
                <span className="truncate uppercase tracking-tight">
                  {bar.name}
                </span>
              </NavLink>
            ))}
          </div>
        </div>
      )}

      <div className="mt-auto" />
      <div className="pt-4 mt-4 border-t-2 border-border flex gap-1">
        <NavLink
          to={ROUTES.SETTINGS}
          className={({ isActive }) =>
            `flex-1 flex items-center gap-3 px-3 py-2 border-2 transition-all text-sm ${
              isActive
                ? "bg-foreground text-background font-black border-border shadow-[2px_2px_0_0_var(--color-success)] -translate-x-0.5 -translate-y-0.5"
                : "text-muted-foreground border-transparent hover:text-foreground hover:bg-muted font-bold"
            }`
          }
        >
          <Settings size={18} />
          <span className="uppercase tracking-tight">{t("nav.settings")}</span>
        </NavLink>
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="flex-shrink-0 flex items-center justify-center w-10 border-2 border-transparent text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
          title="Toggle Theme"
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </nav>
  );
}
