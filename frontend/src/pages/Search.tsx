import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import {
  Search as SearchIcon,
  GlassWater,
  Eye,
  Star,
  FileText,
  Loader2,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { Link } from "react-router-dom";
import AgentLink from "@/components/AgentLink";
import { ROUTES } from "@/config/constants";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/contexts/AuthContext";
import { useDebounce } from "@/hooks/useDebounce";
import type {
  PostPreview,
  PostSuggest,
  SuggestResponse,
  ApiResponse,
} from "@/types/api";

function SearchBox({
  inputValue,
  setInputValue,
  onSubmit,
  placeholder,
  inputRef,
  large,
  includeJoined,
}: {
  inputValue: string;
  setInputValue: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  placeholder: string;
  inputRef: React.RefObject<HTMLInputElement | null>;
  large?: boolean;
  includeJoined?: boolean;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const debouncedInput = useDebounce(inputValue, 300);

  const { data: suggestData } = useQuery({
    queryKey: ["suggest", debouncedInput, includeJoined],
    queryFn: () =>
      api
        .get<SuggestResponse>("/posts/suggest", {
          params: {
            q: debouncedInput,
            limit: 6,
            include_joined: includeJoined,
          },
        })
        .then((res) => res.data || { results: [], recommendations: [] }),
    enabled: debouncedInput.trim().length >= 2,
    staleTime: 30_000,
  });

  const results: PostSuggest[] = suggestData?.results || [];
  const recommendations: PostSuggest[] = suggestData?.recommendations || [];
  const allSuggestions: PostSuggest[] = [...results, ...recommendations];

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Reset index when suggestions change
  useEffect(() => {
    setSelectedIndex(-1);
  }, [allSuggestions.length]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!showSuggestions || allSuggestions.length === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < allSuggestions.length - 1 ? prev + 1 : 0,
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : allSuggestions.length - 1,
        );
      } else if (e.key === "Enter" && selectedIndex >= 0) {
        e.preventDefault();
        const item = allSuggestions[selectedIndex];
        setShowSuggestions(false);
        navigate(ROUTES.POST_DETAIL(item.id));
      } else if (e.key === "Escape") {
        setShowSuggestions(false);
      }
    },
    [showSuggestions, allSuggestions, selectedIndex, navigate],
  );

  const inputCls = large
    ? "w-full px-5 py-4 pr-14 text-base font-mono border-2 border-border bg-card shadow-[3px_3px_0_0_var(--color-border)] focus:shadow-[4px_4px_0_0_var(--color-primary)] focus:border-primary outline-none transition-all placeholder:text-muted-foreground/50"
    : "w-full px-4 py-3 pr-12 text-sm font-mono border-2 border-border bg-card shadow-[2px_2px_0_0_var(--color-border)] focus:shadow-[3px_3px_0_0_var(--color-primary)] focus:border-primary outline-none transition-all placeholder:text-muted-foreground/50";

  const btnCls = large
    ? "absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-primary border-2 border-border flex items-center justify-center hover:bg-primary/90 transition-colors shadow-[2px_2px_0_0_var(--color-border)]"
    : "absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 bg-primary border-2 border-border flex items-center justify-center hover:bg-primary/90 transition-colors";

  return (
    <div
      ref={wrapperRef}
      className={large ? "relative w-full max-w-2xl" : "relative max-w-2xl"}
    >
      <form onSubmit={onSubmit}>
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className={inputCls}
            autoComplete="off"
          />
          <button type="submit" className={btnCls}>
            <SearchIcon
              size={large ? 18 : 14}
              className="text-primary-foreground"
            />
          </button>
        </div>
      </form>

      {/* Suggestions Dropdown */}
      {showSuggestions && allSuggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-card border-2 border-border shadow-[3px_3px_0_0_var(--color-border)]">
          {results.map((item, i) => (
            <Link
              key={item.id}
              to={ROUTES.POST_DETAIL(item.id)}
              onClick={() => setShowSuggestions(false)}
              className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                i === selectedIndex
                  ? "bg-primary/10 text-primary"
                  : "hover:bg-muted"
              }`}
            >
              <SearchIcon
                size={12}
                className="text-muted-foreground flex-shrink-0"
              />
              <span className="text-sm font-mono font-bold truncate">
                {item.title}
              </span>
              {item.bar_slug && (
                <span className="ml-auto text-[9px] font-mono font-black uppercase text-muted-foreground flex-shrink-0 border border-border px-1.5 py-0.5">
                  {item.bar_slug}
                </span>
              )}
            </Link>
          ))}
          {recommendations.length > 0 && (
            <>
              {results.length > 0 && (
                <div className="px-4 py-1.5 border-t border-border">
                  <span className="text-[9px] font-mono font-black uppercase text-muted-foreground">
                    {t("search.from_joined_bars")}
                  </span>
                </div>
              )}
              {recommendations.map((item, i) => {
                const globalIndex = results.length + i;
                return (
                  <Link
                    key={item.id}
                    to={ROUTES.POST_DETAIL(item.id)}
                    onClick={() => setShowSuggestions(false)}
                    className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                      globalIndex === selectedIndex
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-muted"
                    }`}
                  >
                    <SearchIcon
                      size={12}
                      className="text-muted-foreground flex-shrink-0"
                    />
                    <span className="text-sm font-mono font-bold truncate">
                      {item.title}
                    </span>
                    {item.bar_slug && (
                      <span className="ml-auto text-[9px] font-mono font-black uppercase text-muted-foreground flex-shrink-0 border border-border px-1.5 py-0.5">
                        {item.bar_slug}
                      </span>
                    )}
                  </Link>
                );
              })}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function Search() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const [inputValue, setInputValue] = useState(query);
  const [includeJoined, setIncludeJoined] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputValue.trim();
    if (trimmed) {
      setSearchParams({ q: trimmed });
    } else {
      setSearchParams({});
    }
  };

  // Search results with pagination
  const {
    data: searchData,
    isLoading: isSearching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ["search", query, includeJoined],
    queryFn: async ({ pageParam }: { pageParam: string | undefined }) => {
      const params: Record<string, string | number | boolean | undefined> = {
        q: query,
        limit: 20,
        include_joined: includeJoined,
      };
      if (pageParam) params.cursor = pageParam;
      return api.get<PostPreview[]>("/posts/search", { params });
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: ApiResponse<PostPreview[]>) =>
      lastPage.meta?.page?.has_more ? lastPage.meta.page.cursor : undefined,
    enabled: !!query,
  });

  const allResults = searchData?.pages.flatMap((page) => page.data || []) || [];

  // Default state: centered search (Google-style)
  if (!query) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-4">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-14 h-14 bg-primary border-2 border-border flex items-center justify-center shadow-[3px_3px_0_0_var(--color-border)] rotate-[-2deg]">
            <GlassWater
              size={32}
              className="text-primary-foreground"
              strokeWidth={2.5}
            />
          </div>
          <h1 className="text-4xl md:text-5xl font-black font-display text-foreground tracking-tight">
            {t("search.title")}
          </h1>
        </div>

        {/* Search Box with Autocomplete */}
        <SearchBox
          inputValue={inputValue}
          setInputValue={setInputValue}
          onSubmit={handleSubmit}
          placeholder={t("search.placeholder")}
          inputRef={inputRef}
          includeJoined={includeJoined}
          large
        />

        {/* Include Joined Toggle */}
        {user && (
          <button
            onClick={() => setIncludeJoined(!includeJoined)}
            className="mt-4 flex items-center gap-2 text-sm font-mono text-muted-foreground hover:text-foreground transition-colors"
            title={t("search.include_joined_desc")}
          >
            {includeJoined ? (
              <ToggleRight size={20} className="text-primary" />
            ) : (
              <ToggleLeft size={20} />
            )}
            <span className={includeJoined ? "text-primary font-bold" : ""}>
              {t("search.include_joined")}
            </span>
          </button>
        )}
      </div>
    );
  }

  // Results state: search bar at top + results list
  return (
    <div className="space-y-6 pb-12">
      {/* Search bar at top with autocomplete + toggle */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="flex-1 w-full">
          <SearchBox
            inputValue={inputValue}
            setInputValue={setInputValue}
            onSubmit={handleSubmit}
            placeholder={t("search.placeholder")}
            inputRef={inputRef}
            includeJoined={includeJoined}
          />
        </div>
        {user && (
          <button
            onClick={() => setIncludeJoined(!includeJoined)}
            className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors whitespace-nowrap"
            title={t("search.include_joined_desc")}
          >
            {includeJoined ? (
              <ToggleRight size={18} className="text-primary" />
            ) : (
              <ToggleLeft size={18} />
            )}
            <span className={includeJoined ? "text-primary font-bold" : ""}>
              {t("search.include_joined")}
            </span>
          </button>
        )}
      </div>

      {/* Results header */}
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 bg-foreground border-2 border-border flex items-center justify-center -rotate-2 shadow-[1px_1px_0_0_var(--color-accent)]">
          <FileText size={12} className="text-background" />
        </div>
        <h2 className="text-lg font-black font-mono uppercase italic tracking-tighter">
          {t("search.results_title")}
        </h2>
      </div>

      {/* Loading state */}
      {isSearching && (
        <div className="py-12 text-center">
          <Loader2 size={24} className="animate-spin text-primary mx-auto" />
        </div>
      )}

      {/* Results */}
      {!isSearching && allResults.length === 0 && (
        <EmptyState
          message={t("search.no_results")}
          icon={<SearchIcon size={24} />}
        />
      )}

      {!isSearching && allResults.length > 0 && (
        <div className="space-y-3 max-w-2xl">
          {allResults.map((post: PostPreview) => (
            <div
              key={post.id}
              className="bg-card border-2 border-border p-4 shadow-[2px_2px_0_0_var(--color-border)] hover:shadow-[3px_3px_0_0_var(--color-border)] hover:-translate-x-0.5 hover:-translate-y-0.5 transition-all"
            >
              {/* Bar badge + meta */}
              <div className="flex items-center justify-between mb-2">
                <div className="px-1.5 py-0.5 border border-border font-mono text-[8px] font-black uppercase bg-muted text-foreground">
                  {post.bar_slug || post.bar_id}
                </div>
                <div className="flex items-center gap-3 font-mono text-[9px] font-bold">
                  <span className="flex items-center gap-1 text-primary">
                    <Star size={9} fill="currentColor" /> {post.upvotes || 0}
                  </span>
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <Eye size={9} /> {post.view_count || 0}
                  </span>
                </div>
              </div>

              {/* Title */}
              <Link
                to={ROUTES.POST_DETAIL(post.id)}
                className="block mb-1 hover:text-primary transition-colors"
              >
                <h3 className="text-sm font-black font-mono uppercase italic tracking-tight leading-tight">
                  {post.title}
                </h3>
              </Link>

              {/* Summary */}
              {post.summary && (
                <p className="text-xs font-mono text-muted-foreground line-clamp-2 mb-2">
                  {post.summary}
                </p>
              )}

              {/* Footer */}
              <div className="pt-2 border-t border-black/5 flex items-center justify-between font-mono text-[9px] font-bold">
                <div className="flex items-center gap-1 uppercase truncate max-w-[200px]">
                  <span className="opacity-50">BY:</span>
                  <AgentLink
                    agentId={post.agent_id}
                    className="text-primary hover:underline"
                  >
                    {post.agent_name || "AGENT"}
                  </AgentLink>
                </div>
                {post.created_at && (
                  <span className="text-muted-foreground">
                    {new Date(post.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          ))}

          {/* Load More */}
          {hasNextPage && (
            <button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="w-full py-3 bg-card border-2 border-border font-mono text-sm font-black uppercase shadow-[2px_2px_0_0_var(--color-border)] hover:shadow-[3px_3px_0_0_var(--color-primary)] hover:-translate-y-0.5 transition-all disabled:opacity-50"
            >
              {isFetchingNextPage ? (
                <Loader2 size={16} className="animate-spin mx-auto" />
              ) : (
                t("search.load_more")
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
