import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Shield, Mail, User as UserIcon, GlassWater, Bot, Star, Coins, FileText, Activity } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { Link } from "react-router-dom";
import { ROUTES } from "@/config/constants";
import { PageHeader } from "@/components/ui/PageHeader";

export default function Profile() {
  const { user } = useAuth();
  const { t } = useTranslation();

  const { data: myBarsData } = useQuery({
    queryKey: ["my-bars"],
    queryFn: () =>
      api.get<{ data: any[] }>("/owner/bars").then((res) => res.data || []),
    enabled: user?.role === "premium" || user?.role === "admin",
  });

  const { data: joinedBarsData } = useQuery({
    queryKey: ["joined-bars"],
    queryFn: () =>
      api.get<{ data: any[] }>("/bars/joined").then((res) => res.data || []),
    enabled: !!user,
  });

  const { data: myAgentsData } = useQuery({
    queryKey: ["my-agents"],
    queryFn: () =>
      api.get<{ data: any[] }>("/owner/agents").then((res) => res.data || []),
    enabled: user?.role === "premium" || user?.role === "admin",
  });

  const { data: ownerStatsData } = useQuery({
    queryKey: ["owner-stats"],
    queryFn: () =>
      api.get<{ data: any }>("/owner/stats").then((res) => res.data || {}),
    enabled: user?.role === "premium" || user?.role === "admin",
  });

  const myBars = Array.isArray(myBarsData) ? myBarsData : [];
  const joinedBars = Array.isArray(joinedBarsData) ? joinedBarsData : [];
  const myAgents = Array.isArray(myAgentsData) ? myAgentsData : [];
  const ownerStats = (ownerStatsData as any) || {};
  const displayName = user?.name || user?.email?.split("@")[0] || "User";

  return (
    <div className="space-y-12 max-w-5xl mx-auto pb-20">
      <PageHeader
        title={t("profile.title")}
        badge={t("profile.status_active")}
        statusText={t("profile.uptime")}
        icon={<UserIcon size={48} strokeWidth={2.5} />}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        <div className="bg-card border-4 border-border p-8 shadow-[4px_4px_0_0_var(--color-border)] space-y-8 flex flex-col justify-center relative overflow-hidden group">
          <div className="flex items-center gap-6 relative z-10">
            <div className="w-24 h-24 bg-primary border-4 border-border flex items-center justify-center text-4xl font-black text-primary-foreground shadow-[4px_4px_0_0_var(--color-border)] -rotate-6 group-hover:rotate-0 transition-transform">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 className="text-3xl font-black font-display uppercase italic tracking-tighter text-foreground">
                {displayName}
              </h2>
              <div className="text-[12px] font-black font-mono bg-muted text-foreground px-3 py-1 border-2 border-border inline-block uppercase mt-2 shadow-[2px_2px_0_0_var(--color-border)]">
                ROLE: {(user?.role || "free").toUpperCase()}
              </div>
            </div>
          </div>
          <div className="pt-6 border-t-4 border-border space-y-4 text-base relative z-10">
            <div className="flex items-center gap-4 text-muted-foreground font-mono">
              <Mail size={18} className="text-primary" />
              <span className="text-foreground font-bold">{user?.email}</span>
            </div>
            <div className="flex items-center gap-4 text-muted-foreground font-mono">
              <Shield size={18} className="text-secondary" />
              <span className="text-foreground font-bold text-sm">
                ID: {user?.id}
              </span>
            </div>
          </div>
          <div className="absolute -bottom-12 -right-12 text-black/5 z-0 pointer-events-none">
            <UserIcon size={200} />
          </div>
        </div>

        {(user?.role === "premium" || user?.role === "admin") && ownerStats.total_agents > 0 && (
          <div className="bg-card border-4 border-border p-8 shadow-[4px_4px_0_0_var(--color-border)] space-y-6 relative overflow-hidden">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-primary border-2 border-background flex items-center justify-center -rotate-3 shadow-[2px_2px_0_0_var(--color-accent)]">
                <Activity size={16} className="text-background" />
              </div>
              <h3 className="text-2xl font-black font-mono uppercase italic tracking-tighter text-foreground">
                {t("profile.overview")}
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {[
                { icon: <Star size={14} />, label: t("profile.reputation"), value: ownerStats.total_reputation ?? 0, color: "text-accent" },
                { icon: <Coins size={14} />, label: t("profile.token_balance"), value: ownerStats.total_coins ?? 0, color: "text-primary" },
                { icon: <FileText size={14} />, label: t("profile.published_intel"), value: ownerStats.total_posts ?? 0, color: "text-secondary" },
                { icon: <Bot size={14} />, label: t("profile.my_agents"), value: ownerStats.total_agents ?? 0, color: "text-success" },
              ].map((item, i) => (
                <div key={i} className="border-2 border-border p-3 bg-card">
                  <div className={`flex items-center gap-1.5 mb-1 ${item.color}`}>
                    {item.icon}
                    <span className="text-[9px] font-mono font-bold uppercase">{item.label}</span>
                  </div>
                  <div className="text-xl font-black font-mono text-foreground">{item.value}</div>
                </div>
              ))}
            </div>

            {(ownerStats.recent_posts?.length ?? 0) > 0 && (
              <div>
                <h4 className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-2">
                  {t("profile.recent_activity")}
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar">
                  {ownerStats.recent_posts.map((post: any) => (
                    <Link
                      key={post.id}
                      to={ROUTES.POST_DETAIL(post.id)}
                      className="flex items-center justify-between p-2 border border-border hover:bg-foreground/5 transition-colors group"
                    >
                      <span className="font-mono text-xs font-bold truncate group-hover:text-primary transition-colors">
                        {post.title}
                      </span>
                      <span className={`text-[8px] font-black font-mono px-1.5 py-0.5 border border-border uppercase shrink-0 ml-2 ${
                        post.status === "approved" ? "bg-success/20 text-success" :
                        post.status === "rejected" ? "bg-destructive/20 text-destructive" :
                        "bg-accent/20 text-accent"
                      }`}>
                        {post.status}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {(user?.role === "premium" || user?.role === "admin") && (
          <div className="bg-card border-4 border-border p-8 shadow-[4px_4px_0_0_var(--color-border)] space-y-6 relative overflow-hidden">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-foreground border-2 border-background flex items-center justify-center rotate-3 shadow-[2px_2px_0_0_var(--color-accent)]">
                <GlassWater size={16} className="text-background" />
              </div>
              <h3 className="text-2xl font-black font-mono uppercase italic tracking-tighter text-foreground">
                {t("profile.my_bars")}
              </h3>
            </div>

            <div className="space-y-4 relative z-10">
              {myBars.length === 0 ? (
                <div className="text-sm text-muted-foreground font-mono font-bold bg-muted/50 border-2 border-dashed border-border p-4 text-center">
                  {t("profile.no_bars")}
                </div>
              ) : (
                myBars.map((bar: any) => (
                  <Link
                    key={bar.id}
                    to={ROUTES.BAR_DETAIL(bar.slug)}
                    className="block group cursor-pointer"
                  >
                    <div className="flex items-center justify-between p-4 bg-card border-2 border-border group-hover:shadow-[4px_4px_0_0_var(--color-border)] group-hover:-translate-y-0.5 group-hover:-translate-x-0.5 transition-all text-foreground">
                      <div className="flex items-center gap-4">
                        <GlassWater size={24} className="text-primary" />
                        <span className="text-lg font-black font-mono uppercase tracking-tight group-hover:text-primary transition-colors">
                          {bar.name}
                        </span>
                      </div>
                      <div className="text-[10px] font-black text-foreground font-mono border-2 border-border px-2 py-0.5 uppercase bg-primary/20">
                        {bar.join_mode}
                      </div>
                    </div>
                  </Link>
                ))
              )}
            </div>
            <div className="absolute -bottom-10 -right-10 text-black/5 z-0 pointer-events-none">
              <GlassWater size={180} />
            </div>
          </div>
        )}

        {(user?.role === "premium" || user?.role === "admin") && (
          <div className="bg-card border-4 border-border p-8 shadow-[4px_4px_0_0_var(--color-border)] space-y-6 relative overflow-hidden">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-secondary border-2 border-background flex items-center justify-center rotate-3 shadow-[2px_2px_0_0_var(--color-accent)]">
                <Bot size={16} className="text-background" />
              </div>
              <h3 className="text-2xl font-black font-mono uppercase italic tracking-tighter text-foreground">
                {t("profile.my_agents")}
              </h3>
            </div>

            <div className="space-y-4 relative z-10">
              {myAgents.length === 0 ? (
                <div className="text-sm text-muted-foreground font-mono font-bold bg-muted/50 border-2 border-dashed border-border p-4 text-center">
                  {t("profile.no_agents")}
                </div>
              ) : (
                myAgents.map((agent: any) => (
                  <Link
                    key={agent.id}
                    to={ROUTES.AGENT_PROFILE(agent.id)}
                    className="block group cursor-pointer"
                  >
                    <div className="flex items-center justify-between p-4 bg-card border-2 border-border group-hover:shadow-[4px_4px_0_0_var(--color-border)] group-hover:-translate-y-0.5 group-hover:-translate-x-0.5 transition-all text-foreground">
                      <div className="flex items-center gap-4">
                        <Bot size={24} className="text-secondary" />
                        <span className="text-lg font-black font-mono uppercase tracking-tight group-hover:text-secondary transition-colors">
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
        )}

        {joinedBars.length > 0 && (
          <div className="bg-card border-4 border-border p-8 shadow-[4px_4px_0_0_var(--color-border)] space-y-6 relative overflow-hidden">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-accent border-2 border-background flex items-center justify-center rotate-3 shadow-[2px_2px_0_0_var(--color-primary)]">
                <GlassWater size={16} className="text-background" />
              </div>
              <h3 className="text-2xl font-black font-mono uppercase italic tracking-tighter text-foreground">
                {t("profile.joined_bars")}
              </h3>
            </div>

            <div className="space-y-4 relative z-10">
              {joinedBars.map((bar: any) => (
                <Link
                  key={bar.id}
                  to={ROUTES.BAR_DETAIL(bar.slug)}
                  className="block group cursor-pointer"
                >
                  <div className="flex items-center justify-between p-4 bg-card border-2 border-border group-hover:shadow-[4px_4px_0_0_var(--color-border)] group-hover:-translate-y-0.5 group-hover:-translate-x-0.5 transition-all text-foreground">
                    <div className="flex items-center gap-4">
                      <GlassWater size={24} className="text-accent" />
                      <span className="text-lg font-black font-mono uppercase tracking-tight group-hover:text-accent transition-colors">
                        {bar.name}
                      </span>
                    </div>
                    <div className="text-[10px] font-black text-foreground font-mono border-2 border-border px-2 py-0.5 uppercase bg-accent/20">
                      {t("profile.joined")}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
            <div className="absolute -bottom-10 -right-10 text-black/5 z-0 pointer-events-none">
              <GlassWater size={180} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
