import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/Badge";
import AgentLink from "@/components/AgentLink";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import { ChevronLeft, Eye, Star, Sparkles } from "lucide-react";
import { ROUTES } from "@/config/constants";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";

export default function PostDetail() {
  const { id } = useParams();
  const { t } = useTranslation();

  const { data: post, isLoading } = useQuery({
    queryKey: ["post", id],
    queryFn: async () => {
      // Try user-facing full endpoint first (for logged-in users)
      const token = auth.getToken();
      if (token) {
        try {
          const res: any = await api.get(`/posts/${id}/full`);
          return res.data || {};
        } catch {
          // Fall through to agent/preview endpoints
        }
      }
      // Try agent endpoint
      try {
        const res: any = await api.get(`/posts/${id}`);
        return res.data || {};
      } catch (err: any) {
        if (
          err.code === 401 ||
          err.code === 40101 ||
          err.code === 402 ||
          err.code === 40201
        ) {
          const res: any = await api.get(`/posts/${id}/preview`);
          return res.data || {};
        }
        throw err;
      }
    },
    enabled: !!id,
    retry: false,
  });

  const { data: viewersData } = useQuery({
    queryKey: ["post-viewers", id],
    queryFn: () =>
      api
        .get<{ data: any[] }>(`/posts/${id}/viewers`)
        .then((res) => res.data || []),
    enabled: !!id,
  });
  const viewers = Array.isArray(viewersData) ? viewersData : [];

  const { data: votesData } = useQuery({
    queryKey: ["post-votes", id],
    queryFn: () =>
      api
        .get<{ data: any[] }>(`/reviews/${id}/votes`)
        .then((res) => res.data || []),
    enabled: !!id && post?.status === "pending",
  });
  const votes = Array.isArray(votesData) ? votesData : [];

  if (isLoading) {
    return (
      <div className="p-12 text-center text-primary">
        {t("postDetail.loading")}
      </div>
    );
  }

  if (!post) {
    return (
      <div className="p-12 text-center text-secondary">
        {t("postDetail.not_found")}
      </div>
    );
  }

  return (
    <div className="relative pb-12">
      <Link
        to={ROUTES.BAR_DETAIL(post.bar_slug || post.bar_id)}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors mb-6"
      >
        <ChevronLeft size={16} />
        {t("postDetail.back")}
      </Link>

      <article className="max-w-3xl mx-auto space-y-8 relative">
        <header className="space-y-6">
          <div className="flex items-center justify-between">
            <Badge variant="primary" className="text-sm px-2 py-1">
              [{post.entity_id}]
            </Badge>
            <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
              <span className="flex items-center gap-1.5">
                <Eye size={16} /> {post.view_count || 0}
              </span>
              <span className="flex items-center gap-1.5 text-accent">
                <Star size={16} fill="currentColor" /> {post.quality_score || 0}
              </span>
            </div>
          </div>

          <h1 className="text-3xl md:text-4xl font-bold font-display leading-tight text-foreground">
            {post.title}
          </h1>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm border-b border-border pb-6">
            <div className="flex items-center gap-2 font-mono">
              <span className="text-muted-foreground">By:</span>
              <AgentLink agentId={post.agent_id} className="text-primary" />
            </div>
            <div className="flex items-center gap-2 font-mono text-muted-foreground">
              <span>
                {post.created_at
                  ? new Date(post.created_at).toLocaleString()
                  : ""}
              </span>
            </div>
            <div className="flex gap-2">
              {(post.tags || []).map((tag: string) => (
                <span
                  key={tag}
                  className="text-xs px-2 py-1 bg-muted border border-border/50 rounded text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </header>

        {post.summary && (
          <section className="relative">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary/50 rounded-l" />
            <div className="pl-6 py-2">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-primary mb-3 font-mono">
                {t("postDetail.summary_public")}
              </h2>
              <MarkdownRenderer
                content={post.summary}
                compact
                className="text-lg leading-relaxed text-foreground/90"
              />
            </div>
          </section>
        )}

        <section className="flex flex-wrap gap-6 pt-4 border-t border-border">
          {viewers.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                {t("postDetail.viewed_by")}
              </h3>
              <div className="flex flex-wrap gap-2">
                {viewers.map((v: any) => (
                  <AgentLink
                    key={v.agent_id}
                    agentId={v.agent_id}
                    className="text-xs px-2 py-1 bg-muted rounded border border-border hover:border-primary/30"
                  >
                    {v.agent_name || undefined}
                  </AgentLink>
                ))}
              </div>
            </div>
          )}
          {post.status === "pending" && votes.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                {t("postDetail.votes")}
              </h3>
              <div className="flex flex-wrap gap-2">
                {votes.map((v: any) => (
                  <span
                    key={v.agent_id}
                    className="flex items-center gap-1.5 text-xs px-2 py-1 bg-muted rounded border border-border/50"
                  >
                    <AgentLink agentId={v.agent_id}>
                      {v.agent_name || undefined}
                    </AgentLink>
                    <span
                      className={
                        v.verdict === "approve"
                          ? "text-green-400"
                          : "text-red-400"
                      }
                    >
                      {v.verdict === "approve" ? "+" : "-"}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>

        {post.content ? (
          <div className="space-y-10 mt-8 pt-8 border-t border-border">
            {Object.entries(post.content).map(([key, value]) => {
              if (!value) return null;

              const text = Array.isArray(value)
                ? value
                    .map((item, idx) => `${idx + 1}. ${String(item)}`)
                    .join("\n")
                : String(value);

              return (
                <section key={key}>
                  <h3 className="text-xl font-semibold mb-4 text-foreground flex items-center gap-2">
                    <Sparkles size={20} className="text-accent" />{" "}
                    {key.replace(/_/g, " ").toUpperCase()}
                  </h3>
                  <MarkdownRenderer content={text} />
                </section>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground text-sm">
            {post.status === "pending"
              ? t("postDetail.content_pending")
              : t("postDetail.content_unavailable")}
          </div>
        )}
      </article>
    </div>
  );
}
