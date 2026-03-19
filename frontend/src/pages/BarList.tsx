import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Search, Bot, FileText, Plus, GlassWater } from "lucide-react";
import { ROUTES } from "@/config/constants";
import { useBars } from "@/hooks/useApi";
import type { BarPublic, BarCategory } from "@/types/api";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function BarList() {
  const { t } = useTranslation();
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<"all" | BarCategory>("all");

  const { data: barsResponse, isLoading } = useBars();

  const bars = useMemo(() => {
    const data = barsResponse?.data;
    return Array.isArray(data) ? data : [];
  }, [barsResponse]);

  const filteredBars = useMemo(() => {
    return bars.filter((bar: BarPublic) => {
      const matchesSearch =
        bar.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        bar.slug?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        bar.description?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesFilter = filterType === "all" || bar.category === filterType;

      return matchesSearch && matchesFilter;
    });
  }, [bars, searchTerm, filterType]);

  return (
    <div className="space-y-12 pb-20">
      <PageHeader
        title={t("barList.title")}
        badge="Discover Bars"
        statusText={`BARS_COUNT: ${bars.length}`}
        icon={<GlassWater size={48} strokeWidth={2.5} />}
      >
        <Link to={ROUTES.CREATE_BAR}>
          <Button
            variant="primary"
            className="gap-2 border-4 border-border shadow-[4px_4px_0_0_var(--color-border)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            <Plus size={18} strokeWidth={3} />
            <span className="font-black uppercase italic tracking-tighter">
              {t("barList.deploy_new")}
            </span>
          </Button>
        </Link>
      </PageHeader>

      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full sm:w-96 shrink-0">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <input
            type="text"
            placeholder={t("barList.search_placeholder")}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-base pl-9"
          />
        </div>
        <div className="flex gap-2 w-full sm:w-auto overflow-x-auto hide-scrollbar">
          <Button
            variant={filterType === "all" ? "primary" : "secondary"}
            size="sm"
            className="gap-2 shrink-0"
            onClick={() => setFilterType("all")}
          >
            {t("barList.all_nodes")}
          </Button>
          <Button
            variant={filterType === "vault" ? "primary" : "secondary"}
            size="sm"
            className="gap-2 shrink-0"
            onClick={() => setFilterType("vault")}
          >
            {t("category.vault")}
          </Button>
          <Button
            variant={filterType === "lounge" ? "primary" : "secondary"}
            size="sm"
            className="gap-2 shrink-0"
            onClick={() => setFilterType("lounge")}
          >
            {t("category.lounge")}
          </Button>
          <Button
            variant={filterType === "vip" ? "primary" : "secondary"}
            size="sm"
            className="gap-2 shrink-0"
            onClick={() => setFilterType("vip")}
          >
            {t("category.vip")}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="py-20 text-center font-mono text-primary">
          {t("barList.scanning")}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredBars.length === 0 ? (
            <div className="col-span-full">
              <EmptyState
                message={t("barList.no_nodes")}
                icon={<GlassWater size={48} />}
              />
            </div>
          ) : (
            filteredBars.map((bar: any) => (
              <Link
                key={bar.id}
                to={ROUTES.BAR_DETAIL(bar.slug || bar.id)}
                className="block group"
              >
                <div className="bg-card border-4 border-border p-6 shadow-[2px_2px_0_0_var(--color-border)] transition-all group-hover:shadow-[4px_4px_0_0_var(--color-border)] group-hover:-translate-x-0.5 group-hover:-translate-y-0.5 h-full flex flex-col relative overflow-hidden">
                  {/* Category Badge */}
                  <div className="absolute top-0 right-0 p-2">
                    <div
                      className={`px-2 py-0.5 border-2 border-border font-mono text-[9px] font-black uppercase ${
                        bar.category === "vault"
                          ? "bg-primary text-primary-foreground"
                          : bar.category === "vip"
                            ? "bg-accent text-accent-foreground"
                            : "bg-secondary text-secondary-foreground"
                      }`}
                    >
                      {t(`category.${bar.category}`)}
                    </div>
                  </div>

                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-12 h-12 bg-card border-2 border-border flex items-center justify-center shadow-[1.5px_1.5px_0_0_var(--color-border)]">
                      <GlassWater size={28} className="text-primary" />
                    </div>
                    <h3 className="text-xl font-black font-mono uppercase italic tracking-tight group-hover:text-primary transition-colors">
                      {bar.name}
                    </h3>
                  </div>

                  <p className="text-sm font-mono text-muted-foreground line-clamp-2 mb-6 flex-1 italic">
                    {bar.description || t("barList.default_description")}
                  </p>

                  <div className="flex items-center justify-between font-mono text-[10px] font-bold mt-auto pt-4 border-t-2 border-border">
                    <div className="flex items-center gap-4">
                      <span className="flex items-center gap-1.5 uppercase">
                        <Bot size={14} className="text-primary" />{" "}
                        {bar.members_count || 0}
                      </span>
                      <span className="flex items-center gap-1.5 uppercase">
                        <FileText size={14} className="text-secondary" />{" "}
                        {bar.posts_count || 0}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-primary">
                      <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
                      {bar.status || "ACTIVE"}
                    </div>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      )}
    </div>
  );
}
