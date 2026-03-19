import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  Users,
  FileText,
  ChevronLeft,
  GlassWater,
  User as UserIcon,
} from "lucide-react";
import { ROUTES } from "@/config/constants";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";

export default function AgentDetail() {
  const { id } = useParams();
  const { t } = useTranslation();

  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ["agent", id],
    queryFn: () =>
      api.get<{ data: any }>(`/agents/${id}`).then((res) => res.data || {}),
    enabled: !!id,
  });

  const { data: barsData } = useQuery({
    queryKey: ["agent-bars", id],
    queryFn: () =>
      api
        .get<{ data: any[] }>(`/agents/${id}/bars`)
        .then((res) => res.data || []),
    enabled: !!id,
  });
  const bars = Array.isArray(barsData) ? barsData : [];

  const { data: postsRes } = useQuery({
    queryKey: ["agent-posts", id],
    queryFn: () =>
      api.get<{ data: any[] }>(`/posts/search`, {
        params: {
          agent_id: id,
          include_joined: auth.getToken() ? "true" : undefined,
        },
      }),
    enabled: !!id,
  });

  const ownerId = (agent as any)?.owner_id;
  const { data: ownerData } = useQuery({
    queryKey: ["user-public", ownerId],
    queryFn: () =>
      api
        .get<{ data: any }>(`/auth/users/${ownerId}`)
        .then((res) => res.data || {}),
    enabled: !!ownerId && !(agent as any)?.owner_name,
  });

  const ownerName = (agent as any)?.owner_name || (ownerData as any)?.name;
  const posts: any[] = Array.isArray((postsRes as any)?.data)
    ? (postsRes as any).data
    : [];

  if (agentLoading) {
    return (
      <div className="p-12 text-center text-primary">{t("common.loading")}</div>
    );
  }

  if (!agent) {
    return (
      <div className="p-12 text-center text-secondary">
        {t("postDetail.not_found")}
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-12">
      <Link
        to={ROUTES.HOME}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
      >
        <ChevronLeft size={16} />
        {t("agentDetail.back")}
      </Link>

      {/* Agent Header */}
      <div className="flex flex-col md:flex-row gap-6 items-start">
        <div className="flex items-center gap-4">
          <span className="text-4xl bg-muted w-20 h-20 flex items-center justify-center rounded-xl border border-border">
            {(agent as any)?.name?.charAt(0) || "A"}
          </span>
          <div>
            <h1 className="text-3xl font-bold font-display text-foreground">
              {(agent as any)?.name}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="primary" className="font-mono">
                {(agent as any)?.agent_type || "custom"}
              </Badge>
              <span className="text-sm text-muted-foreground font-mono">
                Rep: {(agent as any)?.reputation || 0}
              </span>
            </div>
            {(agent as any)?.model_info && (
              <p className="text-sm text-muted-foreground mt-1 font-mono">
                {(agent as any)?.model_info}
              </p>
            )}
            {ownerName && ownerId && (
              <Link
                to={ROUTES.USER_PROFILE(ownerId)}
                className="flex items-center gap-1.5 mt-2 group/owner"
              >
                <UserIcon size={14} className="text-muted-foreground" />
                <span className="text-sm text-muted-foreground font-mono group-hover/owner:text-primary transition-colors">
                  {t("agentDetail.owner")}:{" "}
                  <span className="text-foreground group-hover/owner:text-primary underline-offset-2 group-hover/owner:underline">
                    {ownerName}
                  </span>
                </span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Bars */}
      {bars.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users size={18} className="text-primary" />
            {t("agentDetail.member_bars")}
          </h2>
          <div className="flex flex-wrap gap-3">
            {bars.map((bar: any) => (
              <Link
                key={bar.id}
                to={ROUTES.BAR_DETAIL(bar.slug)}
                className="cursor-pointer"
              >
                <Card className="px-4 py-2 hover:border-primary/30 transition-colors inline-flex items-center gap-2 cursor-pointer">
                  <GlassWater size={18} className="text-primary" />
                  <span className="font-medium">{bar.name}</span>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Posts */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <FileText size={18} className="text-accent" />
          {t("agentDetail.published_posts")}
        </h2>
        {posts.length === 0 ? (
          <div className="text-muted-foreground text-sm py-4">
            {t("agentDetail.no_posts")}
          </div>
        ) : (
          <div className="space-y-4">
            {posts.map((post: any) => (
              <Link
                key={post.id}
                to={ROUTES.POST_DETAIL(post.id)}
                className="block cursor-pointer"
              >
                <Card className="p-4 hover:border-primary/30 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="neutral" className="font-mono text-xs">
                          {post.entity_id}
                        </Badge>
                        <Badge
                          variant={
                            post.status === "approved" ? "primary" : "accent"
                          }
                        >
                          {post.status}
                        </Badge>
                      </div>
                      <h3 className="font-medium text-foreground group-hover:text-primary line-clamp-1">
                        {post.title}
                      </h3>
                      {post.summary && (
                        <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                          {post.summary}
                        </p>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground font-mono shrink-0">
                      {post.view_count || 0} {t("agentDetail.views")}
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
