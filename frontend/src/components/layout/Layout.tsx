import { useState } from "react";
import { Outlet, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import Navbar from "./Navbar";
import EventsTicker from "@/components/EventsTicker";
import { LAYOUT, ROUTES } from "@/config/constants";
import { Menu, GlassWater } from "lucide-react";

export default function Layout() {
  const { t } = useTranslation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="h-screen flex flex-col w-full bg-background text-foreground overflow-hidden">
      <EventsTicker />
      <div className="flex flex-1 min-h-0">
        {/* Backdrop overlay */}
        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black/30 z-40 md:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}

        <aside
          className={`${LAYOUT.SIDEBAR_WIDTH_MD} flex-shrink-0 flex flex-col border-r border-border bg-card/95 backdrop-blur-xl absolute md:relative z-50 h-full transition-transform duration-300 md:translate-x-0 ${isMobileMenuOpen ? "translate-x-0 w-64" : "-translate-x-full hidden md:flex"}`}
        >
          <div className="p-4 h-full flex flex-col">
            <div className="mb-5">
              <Link to={ROUTES.HOME} onClick={() => setIsMobileMenuOpen(false)}>
                <h1 className="text-lg font-bold font-display text-primary flex items-center gap-2">
                  <GlassWater size={22} strokeWidth={2.5} />
                  {t("layout.title")}
                </h1>
              </Link>
            </div>
            <div
              className="flex-1 flex flex-col min-h-0"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              <Navbar />
            </div>
          </div>
        </aside>

        <main className="flex-1 flex flex-col min-w-0 overflow-y-auto relative z-0">
          <header className="md:hidden flex items-center justify-between p-4 border-b border-border bg-card backdrop-blur-sm sticky top-0 z-10 w-full">
            <Link to={ROUTES.HOME}>
              <h1 className="text-xl font-bold font-display text-primary flex items-center gap-2">
                <GlassWater size={24} strokeWidth={2.5} />
                {t("layout.title")}
              </h1>
            </Link>
            <button
              className="p-2"
              aria-label={t("layout.open_menu")}
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              <Menu size={24} />
            </button>
          </header>

          <div
            className={`flex-1 p-3 md:p-6 ${LAYOUT.MAX_WIDTH} mx-auto w-full`}
          >
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
