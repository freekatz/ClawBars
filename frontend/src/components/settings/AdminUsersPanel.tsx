import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Users, Mail, Check, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { Link } from "react-router-dom";
import { ROUTES } from "@/config/constants";

const PAGE_SIZE = 5;

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-destructive text-destructive-foreground",
  premium: "bg-primary text-primary-foreground",
  free: "bg-muted text-foreground",
};

export default function AdminUsersPanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pendingRoles, setPendingRoles] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const { data: usersData, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () =>
      api.get<{ data: any[] }>("/admin/users").then((res) => res.data || []),
  });

  const updateRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.put(`/admin/users/${userId}/role`, { role }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setPendingRoles((prev) => {
        const next = { ...prev };
        delete next[variables.userId];
        return next;
      });
    },
  });

  const allUsers = Array.isArray(usersData) ? usersData : [];

  const filtered = useMemo(() => {
    if (!search.trim()) return allUsers;
    const q = search.toLowerCase();
    return allUsers.filter(
      (u: any) =>
        (u.id || "").toLowerCase().includes(q) ||
        (u.name || "").toLowerCase().includes(q) ||
        (u.email || "").toLowerCase().includes(q)
    );
  }, [allUsers, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // Reset page when search changes
  const handleSearch = (v: string) => {
    setSearch(v);
    setPage(0);
  };

  return (
    <div className="bg-card border-2 border-border p-4 shadow-[2px_2px_0_0_var(--color-border)]">
      <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-primary mb-4 flex items-center gap-1.5">
        <span className="w-2 h-2 bg-primary rotate-45 inline-block" />
        <Users size={14} />
        {t("settings.admin_users")}
        {allUsers.length > 0 && (
          <span className="text-muted-foreground ml-auto">{allUsers.length}</span>
        )}
      </h3>

      {/* Search */}
      {!isLoading && allUsers.length > 0 && (
        <div className="relative mb-3">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder={t("settings.search_users")}
            className="w-full bg-card text-foreground border-2 border-border pl-7 pr-2 py-1.5 text-[10px] font-mono focus:outline-none focus:shadow-[2px_2px_0_0_var(--color-primary)]"
          />
        </div>
      )}

      {isLoading ? (
        <div className="text-muted-foreground text-sm py-4 font-mono">
          {t("common.loading")}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-muted-foreground text-sm py-4 font-mono">
          {t("settings.no_users")}
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {paged.map((u: any) => (
              <div
                key={u.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 min-h-14 border-2 border-border hover:bg-foreground/5 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 bg-primary border-2 border-border flex items-center justify-center font-black text-primary-foreground text-sm shrink-0">
                    {(u.name || "U").charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <Link
                      to={ROUTES.USER_PROFILE(u.id)}
                      className="font-bold font-mono text-sm uppercase hover:text-primary transition-colors block truncate"
                    >
                      {u.name || u.email}
                    </Link>
                    <div className="flex items-center gap-1 text-[9px] text-muted-foreground font-mono truncate">
                      <Mail size={9} />
                      {u.email}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <div
                    className={`text-[9px] font-black font-mono px-2 py-0.5 border border-border uppercase ${ROLE_COLORS[pendingRoles[u.id] || u.role] || ROLE_COLORS.free}`}
                  >
                    {pendingRoles[u.id] || u.role}
                  </div>
                  <select
                    value={pendingRoles[u.id] || u.role}
                    onChange={(e) => {
                      const newRole = e.target.value;
                      setPendingRoles((prev) =>
                        newRole === u.role
                          ? (() => { const next = { ...prev }; delete next[u.id]; return next; })()
                          : { ...prev, [u.id]: newRole }
                      );
                    }}
                    className="bg-card text-foreground border-2 border-border px-2 py-1 text-[10px] font-mono font-bold uppercase focus:outline-none focus:shadow-[2px_2px_0_0_var(--color-primary)] cursor-pointer"
                  >
                    <option value="free">FREE</option>
                    <option value="premium">PREMIUM</option>
                    <option value="admin">ADMIN</option>
                  </select>
                  {pendingRoles[u.id] && (
                    <button
                      onClick={() =>
                        updateRole.mutate({ userId: u.id, role: pendingRoles[u.id] })
                      }
                      disabled={updateRole.isPending}
                      className="p-1.5 bg-primary text-primary-foreground border-2 border-border shadow-[2px_2px_0_0_var(--color-border)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all"
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
