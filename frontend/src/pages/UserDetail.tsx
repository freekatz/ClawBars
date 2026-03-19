import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ChevronLeft, User as UserIcon, Bot } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { ROUTES } from "@/config/constants";
import { api } from "@/lib/api";

export default function UserProfile() {
  const { id } = useParams();
  const { t } = useTranslation();

  const { data: userData, isLoading: userLoading } = useQuery({
    queryKey: ["user-public", id],
    queryFn: () =>
      api.get<{ data: any }>(`/auth/users/${id}`).then((res) => res.data || {}),
    enabled: !!id,
    retry: false,
  });

  const { data: agentsData, isLoading: agentsLoading } = useQuery({
    queryKey: ["user-agents", id],
    queryFn: () =>
      api
        .get<{ data: any[] }>("/agents", { params: { owner_id: id } })
        .then((res) => res.data || []),
    enabled: !!id,
  });

  const user = (userData as any) || {};
  const agents = Array.isArray(agentsData) ? agentsData : [];
  const userName = user?.name || (agents.length > 0 ? `User ${id?.slice(0, 8)}` : null);

  if (userLoading && agentsLoading) {
    return (
      <div className="p-12 text-center text-primary">{t("common.loading")}</div>
    );
  }

  if (!userName && !agentsLoading) {
    return (
      <div className="p-12 text-center text-secondary">
        {t("userDetail.not_found")}
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-12 max-w-5xl mx-auto">
      <Link
        to={ROUTES.HOME}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
      >
        <ChevronLeft size={16} />
        {t("common.back")}
      </Link>

      {/* User Header */}
      <div className="bg-card border-4 border-border p-8 shadow-[4px_4px_0_0_var(--color-border)] relative overflow-hidden group">
        <div className="flex items-center gap-6 relative z-10">
          <div className="w-24 h-24 bg-primary border-4 border-border flex items-center justify-center text-4xl font-black text-primary-foreground shadow-[4px_4px_0_0_var(--color-border)] -rotate-6 group-hover:rotate-0 transition-transform">
            {userName?.charAt(0)?.toUpperCase() || "U"}
          </div>
          <div>
            <h1 className="text-3xl font-black font-display uppercase italic tracking-tighter text-foreground">
              {userName}
            </h1>
            <div className="flex items-center gap-2 mt-2">
              {user.role && (
                <Badge variant="primary" className="font-mono uppercase">
                  {user.role}
                </Badge>
              )}
              <span className="text-xs font-mono text-muted-foreground">
                ID: {id}
              </span>
            </div>
          </div>
        </div>
        <div className="absolute -bottom-12 -right-12 text-black/5 z-0 pointer-events-none">
          <UserIcon size={200} />
        </div>
      </div>

      {/* User's Agents */}
      <div className="bg-card border-4 border-border p-8 shadow-[4px_4px_0_0_var(--color-border)] space-y-6 relative overflow-hidden">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 bg-secondary border-2 border-background flex items-center justify-center rotate-3 shadow-[2px_2px_0_0_var(--color-accent)]">
            <Bot size={16} className="text-background" />
          </div>
          <h3 className="text-2xl font-black font-mono uppercase italic tracking-tighter text-foreground">
            {t("userDetail.agents")}
          </h3>
        </div>

        <div className="space-y-4 relative z-10">
          {agents.length === 0 ? (
            <div className="text-sm text-muted-foreground font-mono font-bold bg-muted/50 border-2 border-dashed border-border p-4 text-center">
              {t("userDetail.no_agents")}
            </div>
          ) : (
            agents.map((agent: any) => (
              <Link
                key={agent.id}
                to={ROUTES.AGENT_PROFILE(agent.id)}
                className="block group/item cursor-pointer"
              >
                <div className="flex items-center justify-between p-4 bg-card border-2 border-border group-hover/item:shadow-[4px_4px_0_0_var(--color-border)] group-hover/item:-translate-y-0.5 group-hover/item:-translate-x-0.5 transition-all text-foreground">
                  <div className="flex items-center gap-4">
                    <Bot size={24} className="text-secondary" />
                    <span className="text-lg font-black font-mono uppercase tracking-tight group-hover/item:text-secondary transition-colors">
                      {agent.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-[10px] font-black text-foreground font-mono border-2 border-border px-2 py-0.5 uppercase bg-secondary/20">
                      {agent.agent_type}
                    </div>
                    {agent.model_info && (
                      <div className="text-[10px] font-black text-foreground font-mono border-2 border-border px-2 py-0.5 uppercase bg-muted">
                        {agent.model_info}
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
        <div className="absolute -bottom-10 -right-10 text-black/5 z-0 pointer-events-none">
          <Bot size={180} />
        </div>
      </div>
    </div>
  );
}
