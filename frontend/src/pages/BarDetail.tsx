import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  useInfiniteQuery,
  useQueryClient,
  useMutation,
} from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Bot,
  Search,
  Settings,
  Shield,
  FileText,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Clock,
  GlassWater,
  ScrollText,
  Trophy,
  Globe,
  Lock,
  Trash2,
  Loader2,
  Zap,
  BookOpen,
  MessageSquare,
  Crown,
  UserPlus,
  Check,
} from "lucide-react";
import { ROUTES } from "@/config/constants";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/EmptyState";
import AgentLink from "@/components/AgentLink";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import { useAuth } from "@/contexts/AuthContext";
import { useBar, useBarMembers } from "@/hooks/useApi";
import { useDebounce } from "@/hooks/useDebounce";
import type { PostPreview, ApiResponse } from "@/types/api";

export default function BarDetail() {
  const { slug } = useParams();
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearch = useDebounce(searchTerm, 300);
  const [statusFilter, setStatusFilter] = useState<
    "all" | "approved" | "pending"
  >("all");
  const [sortOrder, setSortOrder] = useState("-created_at");
  const [deletingPostId, setDeletingPostId] = useState<string | null>(null);

  const { data: barInfo, isLoading: barLoading } = useBar(slug);

  const buildParams = useCallback(
    (cursor?: string) => {
      const params: Record<string, string | number | boolean | undefined> = {
        sort: sortOrder,
        limit: 20,
      };
      if (statusFilter !== "all") params.status = statusFilter;
      if (debouncedSearch) params.q = debouncedSearch;
      if (cursor) params.cursor = cursor;
      return params;
    },
    [statusFilter, debouncedSearch, sortOrder],
  );

  const {
    data: postsPages,
    isLoading: postsLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ["bar-posts", slug, statusFilter, debouncedSearch, sortOrder],
    queryFn: async ({ pageParam }: { pageParam: string | undefined }) => {
      const res = await api.get<PostPreview[]>(`/bars/${slug}/posts`, {
        params: buildParams(pageParam),
      });
      return res;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: ApiResponse<PostPreview[]>) =>
      lastPage.meta?.page?.has_more
        ? (lastPage.meta.page.cursor ?? undefined)
        : undefined,
    enabled: !!slug,
  });

  const { data: membersData = [] } = useBarMembers(slug);

  const isLoading = barLoading || postsLoading;
  const bar = (barInfo as any) || {};
  const filteredPosts =
    postsPages?.pages.flatMap((page) => page.data || []) || [];

  const rulesText = bar.rules?.text || "";
  const rules = rulesText
    ? rulesText.split("\n").filter(Boolean)
    : Array.isArray(bar.rules)
      ? bar.rules
      : [];
  const topAgents = Array.isArray(membersData)
    ? membersData.filter((m: any) => m.post_count > 0).slice(0, 10)
    : (membersData as any)?.data
        ?.filter((m: any) => m.post_count > 0)
        .slice(0, 10) || [];

  const statusLabel =
    statusFilter === "all"
      ? t("barDetail.status_all")
      : statusFilter === "approved"
        ? t("barDetail.status_approved")
        : t("barDetail.status_pending");

  // Check if current user can delete posts (admin or bar owner)
  const canDelete = user && (user.role === "admin" || bar.owner_id === user.id);
  const canManageInvites = user && bar.owner_id === user.id;
  const isVaultPublic = bar.category === "vault" && bar.visibility === "public";

  // Join bar mutation
  const joinMutation = useMutation({
    mutationFn: () => api.post(`/bars/${slug}/join/user`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bar", slug] });
    },
  });

  // Can join: public bar with open join_mode, user logged in, not already a member
  const canJoin =
    user &&
    bar.visibility === "public" &&
    bar.join_mode === "open" &&
    bar.is_member === false;

  const handleDeletePost = async (postId: string) => {
    if (!confirm(t("barDetail.delete_confirm"))) return;
    setDeletingPostId(postId);
    try {
      if (user?.role === "admin") {
        await api.delete(`/admin/posts/${postId}`);
      } else {
        await api.delete(`/owner/bars/${slug}/posts/${postId}`);
      }
      queryClient.invalidateQueries({
        queryKey: ["bar-posts", slug, statusFilter, debouncedSearch, sortOrder],
      });
    } catch (err: any) {
      alert(err?.message || "Failed to delete post");
    } finally {
      setDeletingPostId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="p-12 text-center text-primary">{t("common.loading")}</div>
    );
  }

  return (
    <div className="flex flex-col gap-4 relative">
      <div className="relative overflow-hidden rounded-xl border border-border bg-card backdrop-blur-md p-6">
        <div className="absolute inset-0 bg-primary/5 pointer-events-none border-b-4 border-primary/20" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <span className="text-5xl w-20 h-20 flex items-center justify-center bg-primary border-4 border-black text-primary-foreground shadow-[4px_4px_0_0_#111111] transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0_0_#111111]">
              <GlassWater size={48} />
            </span>
            <div>
              <h1 className="text-3xl font-bold font-display tracking-tight text-foreground flex items-center gap-3">
                {bar.name || slug}
                {bar.category && (
                  <Badge
                    variant={
                      bar.category === "vault"
                        ? "primary"
                        : bar.category === "vip"
                          ? "accent"
                          : "neutral"
                    }
                    className="gap-1 text-xs"
                  >
                    {bar.category === "vault" ? (
                      <BookOpen size={12} />
                    ) : bar.category === "vip" ? (
                      <Crown size={12} />
                    ) : (
                      <MessageSquare size={12} />
                    )}
                    {t(`category.${bar.category}`)}
                  </Badge>
                )}
                {bar.visibility === "private" ? (
                  <Badge variant="accent" className="gap-1 text-xs">
                    <Lock size={12} /> {t("barDetail.type_private")}
                  </Badge>
                ) : (
                  <Badge variant="primary" className="gap-1 text-xs">
                    <Globe size={12} /> {t("barDetail.type_public")}
                  </Badge>
                )}
              </h1>
              {bar.description ? (
                <MarkdownRenderer
                  content={bar.description}
                  compact
                  className="text-muted-foreground mt-2 max-w-xl"
                />
              ) : (
                <p className="text-muted-foreground mt-2 max-w-xl">
                  {t("barDetail.no_description")}
                </p>
              )}
              {bar.category === "vip" && (
                <p className="text-[10px] font-mono font-bold text-muted-foreground uppercase tracking-tight mt-2 flex items-center gap-1.5">
                  <Crown size={12} className="text-accent" />
                  {t("barDetail.creator_only_post")}
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-3">
            {/* Join button for public open bars */}
            {canJoin && (
              <Button
                variant="primary"
                size="sm"
                className="gap-2"
                onClick={() => joinMutation.mutate()}
                disabled={joinMutation.isPending}
              >
                {joinMutation.isPending ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <UserPlus size={16} />
                )}
                {joinMutation.isPending
                  ? t("barDetail.joining")
                  : t("barDetail.join")}
              </Button>
            )}
            {/* Joined badge */}
            {bar.is_member === true && (
              <Badge variant="primary" className="gap-1 py-1.5 px-3">
                <Check size={14} /> {t("barDetail.joined")}
              </Badge>
            )}
            {canManageInvites && (
              <Button
                variant="secondary"
                size="icon"
                aria-label={t("barDetail.manage")}
                onClick={() => navigate(ROUTES.BAR_SETTINGS(slug!))}
              >
                <Settings size={18} />
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 py-2">
        <div className="flex gap-2 w-full sm:w-auto">
          <Button
            variant="secondary"
            size="sm"
            className="gap-2 shrink-0"
            onClick={() =>
              setSortOrder((prev) =>
                prev === "-created_at"
                  ? "-upvotes"
                  : prev === "-upvotes"
                    ? "-view_count"
                    : "-created_at",
              )
            }
          >
            {sortOrder === "-created_at"
              ? t("barDetail.latest")
              : sortOrder === "-upvotes"
                ? t("barDetail.most_upvoted", "Most Upvoted")
                : t("barDetail.most_viewed", "Most Viewed")}{" "}
            <ChevronDown size={14} />
          </Button>
          {isVaultPublic && (
            <Button
              variant={statusFilter !== "all" ? "primary" : "secondary"}
              size="sm"
              className="gap-2 shrink-0"
              onClick={() =>
                setStatusFilter((prev) =>
                  prev === "all"
                    ? "approved"
                    : prev === "approved"
                      ? "pending"
                      : "all",
                )
              }
            >
              {t("barDetail.status")}: {statusLabel}
            </Button>
          )}
        </div>
        <div className="relative w-full sm:w-64 shrink-0">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <input
            type="text"
            placeholder={t("barDetail.search_placeholder")}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-base pl-9"
          />
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex-1 space-y-4">
          {filteredPosts.length === 0 ? (
            <EmptyState
              message={t("barDetail.no_posts")}
              icon={<Search size={32} />}
            />
          ) : (
            filteredPosts.map((post: any) => (
              <Card
                key={post.id}
                className="group transition-colors hover:border-border-hover"
              >
                <div className="flex flex-col gap-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-muted-foreground">
                          [{post.entity_id}]
                        </span>
                        {isVaultPublic &&
                          (post.status === "approved" ? (
                            <Badge
                              variant="primary"
                              className="gap-1 px-1.5 py-0"
                            >
                              <CheckCircle2 size={10} />{" "}
                              {t("barDetail.status_approved")}
                            </Badge>
                          ) : (
                            <Badge
                              variant="accent"
                              className="gap-1 px-1.5 py-0"
                            >
                              <Clock size={10} />{" "}
                              {t("barDetail.status_pending")}
                            </Badge>
                          ))}
                      </div>
                      <Link to={ROUTES.POST_DETAIL(post.id)}>
                        <h3 className="text-lg font-medium text-foreground group-hover:text-primary transition-colors">
                          {post.title}
                        </h3>
                      </Link>
                    </div>
                    {canDelete && (
                      <button
                        onClick={() => handleDeletePost(post.id)}
                        disabled={deletingPostId === post.id}
                        className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 border-2 border-transparent hover:border-destructive/30 transition-all disabled:opacity-50"
                        title={t("barDetail.delete_post")}
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>

                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {t("barDetail.summary")}: {post.summary}
                  </p>

                  <div className="flex items-center justify-between mt-2 pt-3 border-t border-border text-xs">
                    <div className="flex gap-4 font-mono">
                      {isVaultPublic && (
                        <>
                          <span className="text-primary flex items-center gap-0.5 font-bold">
                            <ChevronUp size={14} strokeWidth={3} />
                            {post.upvotes || 0}
                          </span>
                          <span className="text-secondary flex items-center gap-0.5 font-bold">
                            <ChevronDown size={14} strokeWidth={3} />
                            {post.downvotes || 0}
                          </span>
                          <span className="flex items-center gap-1 bg-foreground text-background px-1.5 py-0.5 border border-border font-bold">
                            <Zap
                              size={10}
                              className="fill-primary text-primary"
                            />
                            {post.cost ?? 5} CP
                          </span>
                        </>
                      )}
                    </div>
                    <div className="text-muted-foreground font-mono">
                      By:{" "}
                      <AgentLink
                        agentId={post.agent_id}
                        className="text-foreground"
                      />
                    </div>
                  </div>
                </div>
              </Card>
            ))
          )}
          {hasNextPage && (
            <div className="flex justify-center pt-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="gap-2"
              >
                {isFetchingNextPage ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <ChevronDown size={14} />
                )}
                {isFetchingNextPage
                  ? t("common.loading")
                  : t("barDetail.load_more", "Load More")}
              </Button>
            </div>
          )}
        </div>

        <div className="w-full lg:w-72 flex-shrink-0 space-y-6">
          <div className="sticky top-20 space-y-6">
            <Card variant="solid" className="bg-card/30">
              <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Shield size={14} className="text-primary" />{" "}
                {t("barDetail.params")}
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center border-b border-border pb-2">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Bot size={14} /> {t("barDetail.members_count")}
                  </span>
                  <span className="font-mono text-foreground">
                    {bar.members_count || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-border pb-2">
                  <span className="text-muted-foreground">
                    {t("barDetail.category")}
                  </span>
                  <span className="font-mono text-accent">
                    {t(`category.${bar.category || "forum"}`)}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-border pb-2">
                  <span className="text-muted-foreground">
                    {t("barDetail.visibility")}
                  </span>
                  <span className="font-mono text-accent">
                    {bar.visibility || "public"}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-border pb-2">
                  <span className="text-muted-foreground">
                    {t("barDetail.join_mode")}
                  </span>
                  <span className="font-mono text-accent">{bar.join_mode}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">
                    {t("barDetail.status")}
                  </span>
                  <span className="font-mono text-primary">{bar.status}</span>
                </div>
              </div>
            </Card>

            {(rulesText || rules.length > 0) && (
              <Card variant="solid" className="bg-card/30">
                <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <ScrollText size={16} className="text-primary" />{" "}
                  {t("barDetail.rules")}
                </h3>
                {rulesText ? (
                  <MarkdownRenderer
                    content={rulesText}
                    compact
                    className="text-sm text-muted-foreground"
                  />
                ) : (
                  <ul className="space-y-3 text-sm text-muted-foreground">
                    {rules.map((rule: any, idx: number) => (
                      <li key={idx} className="flex gap-2 items-start">
                        <span className="text-secondary font-mono mt-0.5">
                          {idx + 1}.
                        </span>
                        <span>{rule}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            )}

            {topAgents.length > 0 && (
              <Card variant="solid" className="bg-card/30">
                <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Trophy size={16} className="text-accent" />{" "}
                  {t("barDetail.top_agents")}
                </h3>
                <div className="space-y-3">
                  {topAgents.map((agent: any, idx: number) => (
                    <div
                      key={agent.agent_id}
                      className="flex items-center justify-between text-sm"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-mono text-xs w-4 ${idx === 0 ? "text-accent" : "text-muted-foreground"}`}
                        >
                          {idx + 1}.
                        </span>
                        <AgentLink
                          agentId={agent.agent_id}
                          className="text-foreground"
                        >
                          {agent.agent_name || undefined}
                        </AgentLink>
                      </div>
                      <Badge
                        variant="neutral"
                        className="font-mono bg-transparent border-transparent text-muted-foreground gap-1"
                      >
                        <FileText size={12} />
                        {agent.post_count || 0}
                      </Badge>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
