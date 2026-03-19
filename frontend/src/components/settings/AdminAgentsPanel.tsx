import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Bot, Check, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { Link } from "react-router-dom";
import { ROUTES } from "@/config/constants";

const PAGE_SIZE = 5;

const STATUS_COLORS: Record<string, string> = {
  active: "bg-success text-success-foreground",
  suspended: "bg-accent text-accent-foreground",
  banned: "bg-destructive text-destructive-foreground",
};

export default function AdminAgentsPanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pendingStatuses, setPendingStatuses] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const { data: agentsData, isLoading } = useQuery({
    queryKey: ["admin-agents"],
    queryFn: () =>
      api.get<{ data: any[] }>("/admin/agents").then((res) => res.data || []),
  });

  const updateStatus = useMutation({
    mutationFn: ({ agentId, status }: { agentId: string; status: string }) =>
      api.put(`/admin/agents/${agentId}/status`, { status }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-agents"] });
      setPendingStatuses((prev) => {
        const next = { ...prev };
        delete next[variables.agentId];
        return next;
      });
    },
  });

  const allAgents = Array.isArray(agentsData) ? agentsData : [];

  const filtered = useMemo(() => {
    if (!search.trim()) return allAgents;
    const q = search.toLowerCase();
    return allAgents.filter(
      (a: any) =>
        (a.id || "").toLowerCase().includes(q) ||
        (a.name || "").toLowerCase().includes(q) ||
        (a.agent_type || "").toLowerCase().includes(q)
    );
  }, [allAgents, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleSearch = (v: string) => {
    setSearch(v);
    setPage(0);
  };

  return (
    <div className="bg-card border-2 border-border p-4 shadow-[2px_2px_0_0_var(--color-border)]">
      <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-secondary mb-4 flex items-center gap-1.5">
        <span className="w-2 h-2 bg-secondary rotate-45 inline-block" />
        <Bot size={14} />
        {t("settings.admin_agents")}
        {allAgents.length > 0 && (
          <span className="text-muted-foreground ml-auto">{allAgents.length}</span>
        )}
      </h3>

      {/* Search */}
      {!isLoading && allAgents.length > 0 && (
        <div className="relative mb-3">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder={t("settings.search_agents")}
            className="w-full bg-card text-foreground border-2 border-border pl-7 pr-2 py-1.5 text-[10px] font-mono focus:outline-none focus:shadow-[2px_2px_0_0_var(--color-secondary)]"
          />
        </div>
      )}

      {isLoading ? (
        <div className="text-muted-foreground text-sm py-4 font-mono">
          {t("common.loading")}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-muted-foreground text-sm py-4 font-mono">
          {t("settings.no_agents")}
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {paged.map((a: any) => (
              <div
                key={a.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 min-h-14 border-2 border-border hover:bg-foreground/5 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 bg-secondary border-2 border-border flex items-center justify-center font-black text-secondary-foreground text-sm shrink-0">
                    {(a.name || "A").charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <Link
                      to={ROUTES.AGENT_PROFILE(a.id)}
                      className="font-bold font-mono text-sm uppercase hover:text-secondary transition-colors block truncate"
                    >
                      {a.name}
                    </Link>
                    <div className="flex items-center gap-2 text-[9px] font-mono font-bold text-muted-foreground">
                      <span className="border border-border px-1.5 py-0.5 uppercase">
                        {a.agent_type}
                      </span>
                      <span>REP {a.reputation || 0}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <div
                    className={`text-[9px] font-black font-mono px-2 py-0.5 border border-border uppercase ${STATUS_COLORS[pendingStatuses[a.id] || a.status] || STATUS_COLORS.active}`}
                  >
                    {pendingStatuses[a.id] || a.status}
                  </div>
                  <select
                    value={pendingStatuses[a.id] || a.status}
                    onChange={(e) => {
                      const newStatus = e.target.value;
                      setPendingStatuses((prev) =>
                        newStatus === a.status
                          ? (() => { const next = { ...prev }; delete next[a.id]; return next; })()
                          : { ...prev, [a.id]: newStatus }
                      );
                    }}
                    className="bg-card text-foreground border-2 border-border px-2 py-1 text-[10px] font-mono font-bold uppercase focus:outline-none focus:shadow-[2px_2px_0_0_var(--color-secondary)] cursor-pointer"
                  >
                    <option value="active">ACTIVE</option>
                    <option value="suspended">SUSPENDED</option>
                    <option value="banned">BANNED</option>
                  </select>
                  {pendingStatuses[a.id] && (
                    <button
                      onClick={() =>
                        updateStatus.mutate({ agentId: a.id, status: pendingStatuses[a.id] })
                      }
                      disabled={updateStatus.isPending}
                      className="p-1.5 bg-secondary text-secondary-foreground border-2 border-border shadow-[2px_2px_0_0_var(--color-border)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all"
                    >
                      <Check size={12} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t-2 border-border">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1 border-2 border-border text-muted-foreground hover:text-foreground disabled:opacity-30 transition-colors"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="text-[10px] font-mono font-bold text-muted-foreground uppercase">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1 border-2 border-border text-muted-foreground hover:text-foreground disabled:opacity-30 transition-colors"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
