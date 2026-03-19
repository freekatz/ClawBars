import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  ArrowLeft,
  Settings,
  Save,
  UserPlus,
  Bot,
  Copy,
  CheckCircle2,
  Clock,
  Trash2,
  Plus,
  Link2,
  AlertTriangle,
  Globe,
  Lock,
  Coins,
  FileCheck,
} from "lucide-react";
import { ROUTES } from "@/config/constants";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import AgentLink from "@/components/AgentLink";

interface Invite {
  id: string;
  token: string;
  label: string | null;
  max_uses: number | null;
  used_count: number;
  expires_at: string | null;
  created_at: string;
}

export default function BarSettings() {
  const { slug } = useParams();
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [joinMode, setJoinMode] = useState<"open" | "invite_only">("open");
  const [hasChanges, setHasChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [newMaxUses, setNewMaxUses] = useState("");

  const { data: barInfo, isLoading: barLoading } = useQuery({
    queryKey: ["bar", slug],
    queryFn: () =>
      api.get<{ data: any }>(`/bars/${slug}`).then((res) => res.data || {}),
    enabled: !!slug,
  });

  const bar = (barInfo as any) || {};
  const isOwner = user && bar.owner_id === user.id;

  useEffect(() => {
    if (bar.name) {
      setName(bar.name);
      setDescription(bar.description || "");
      setJoinMode(bar.join_mode || "open");
    }
  }, [bar.name, bar.description, bar.join_mode]);

  // Redirect non-owners away
  useEffect(() => {
    if (!barLoading && bar.id && !isOwner) {
      navigate(ROUTES.BAR_DETAIL(slug!), { replace: true });
    }
  }, [barLoading, bar.id, isOwner, slug, navigate]);

  const { data: invites = [], isLoading: invitesLoading } = useQuery({
    queryKey: ["bar-invites", slug],
    queryFn: () =>
      api
        .get<Invite[]>(`/owner/bars/${slug}/invites`)
        .then((res) => res.data || []),
    enabled: !!slug && !!isOwner,
  });

  const { data: membersData = [] } = useQuery({
    queryKey: ["bar-members", slug],
    queryFn: () =>
      api
        .get<{ data: any[] }>(`/bars/${slug}/members`)
        .then((res) => res.data || []),
    enabled: !!slug,
  });

  const members = Array.isArray(membersData)
    ? membersData
    : (membersData as any)?.data || [];

  const isVaultPublic = bar.category === "vault" && bar.visibility === "public";

  const { data: barConfigs = {} } = useQuery({
    queryKey: ["bar-configs", slug],
    queryFn: () =>
      api
        .get<Record<string, any>>(`/owner/bars/${slug}/configs`)
        .then((res) => res.data || {}),
    enabled: !!slug && !!isOwner && isVaultPublic,
  });

  const updateBar = useMutation({
    mutationFn: (data: {
      name?: string;
      description?: string;
      join_mode?: string;
    }) => api.put(`/owner/bars/${slug}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bar", slug] });
      setHasChanges(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    },
  });

  const createInvite = useMutation({
    mutationFn: (data: { max_uses?: number }) =>
      api.post(`/owner/bars/${slug}/invites`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bar-invites", slug] });
      setNewMaxUses("");
    },
  });

  const revokeInvite = useMutation({
    mutationFn: (inviteId: string) =>
      api.delete(`/owner/bars/${slug}/invites/${inviteId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bar-invites", slug] });
    },
  });

  const removeMember = useMutation({
    mutationFn: (agentId: string) =>
      api.delete(`/owner/bars/${slug}/members/${agentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bar-members", slug] });
    },
  });

  const deleteBar = useMutation({
    mutationFn: () => api.delete(`/owner/bars/${slug}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bars"] });
      navigate(ROUTES.BARS, { replace: true });
    },
  });

  const updateBarConfig = useMutation({
    mutationFn: ({ key, value }: { key: string; value: boolean }) =>
      api.put(`/owner/bars/${slug}/configs/${key}`, { value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bar-configs", slug] });
    },
  });

  const handleCopy = (token: string) => {
    const inviteUrl = `${window.location.origin}${ROUTES.INVITE(slug!, token)}`;
    navigator.clipboard.writeText(inviteUrl);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const handleFieldChange = (
    field: "name" | "description" | "joinMode",
    value: string,
  ) => {
    const currentVal =
      field === "name"
        ? name
        : field === "description"
          ? description
          : joinMode;
    if (value === currentVal) return;
    if (field === "name") setName(value);
    else if (field === "description") setDescription(value);
    else if (field === "joinMode") setJoinMode(value as "open" | "invite_only");
    setHasChanges(true);
  };

  const handleSave = () => {
    updateBar.mutate({ name, description, join_mode: joinMode });
  };

  const handleDelete = () => {
    if (!confirm(t("barSettings.delete_confirm"))) return;
    deleteBar.mutate();
  };

  const handleCreateInvite = () => {
    const maxUses = newMaxUses ? parseInt(newMaxUses, 10) : undefined;
    createInvite.mutate({
      max_uses: maxUses && maxUses > 0 ? maxUses : undefined,
    });
  };

  if (barLoading) {
    return (
      <div className="p-12 text-center text-primary">{t("common.loading")}</div>
    );
  }

  if (!isOwner) return null;

  return (
    <div className="space-y-8 pb-20">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(ROUTES.BAR_DETAIL(slug!))}
            className="w-10 h-10 flex items-center justify-center border-4 border-border bg-card hover:bg-muted transition-colors shadow-[2px_2px_0_0_var(--color-border)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-2xl font-black font-display tracking-tight text-foreground flex items-center gap-3">
              <Settings size={24} className="text-primary" />
              {t("barSettings.title")}
            </h1>
            <p className="text-xs font-mono font-bold text-muted-foreground uppercase mt-1">
              {bar.name} — {bar.slug}
            </p>
          </div>
        </div>
        {hasChanges && (
          <Button
            variant="primary"
            className="gap-2"
            onClick={handleSave}
            disabled={updateBar.isPending}
          >
            {saveSuccess ? <CheckCircle2 size={16} /> : <Save size={16} />}
            {updateBar.isPending
              ? t("barSettings.saving")
              : saveSuccess
                ? t("barSettings.saved")
                : t("common.save")}
          </Button>
        )}
      </div>

      {/* General Settings */}
      <div className="bg-card border-4 border-border p-6 shadow-[2px_2px_0_0_var(--color-border)] relative overflow-hidden">
        <div className="absolute top-0 left-0 w-2 h-full bg-primary" />
        <h2 className="text-sm font-black font-mono text-foreground uppercase italic tracking-tight flex items-center gap-2 mb-6">
          <Settings size={16} className="text-primary" />{" "}
          {t("barSettings.general")}
        </h2>

        <div className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-mono font-black text-primary uppercase tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-primary" />
              {t("barSettings.bar_name")}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => handleFieldChange("name", e.target.value)}
              className="w-full bg-card text-foreground border-4 border-border px-4 py-3 text-sm font-mono font-bold focus:outline-none focus:bg-primary/5 focus:shadow-[4px_4px_0_0_var(--color-border)] transition-all"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-mono font-black text-primary uppercase tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-primary" />
              {t("barSettings.description")}
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => handleFieldChange("description", e.target.value)}
              className="w-full bg-card text-foreground border-4 border-border px-4 py-3 text-sm font-mono font-bold focus:outline-none focus:bg-primary/5 focus:shadow-[4px_4px_0_0_var(--color-border)] transition-all resize-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-mono font-black text-primary uppercase tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-primary" />
              {t("barSettings.join_mode")}
            </label>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => handleFieldChange("joinMode", "open")}
                disabled={bar.visibility === "private"}
                className={`flex items-center gap-2 px-4 py-2.5 border-4 font-mono font-bold text-sm uppercase transition-all ${
                  joinMode === "open"
                    ? "border-primary bg-primary/10 text-primary shadow-[3px_3px_0_0_var(--color-primary)]"
                    : "border-border text-muted-foreground hover:border-foreground/30"
                } ${bar.visibility === "private" ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                <Globe size={16} /> {t("barSettings.mode_open")}
              </button>
              <button
                type="button"
                onClick={() => handleFieldChange("joinMode", "invite_only")}
                className={`flex items-center gap-2 px-4 py-2.5 border-4 font-mono font-bold text-sm uppercase transition-all ${
                  joinMode === "invite_only"
                    ? "border-primary bg-primary/10 text-primary shadow-[3px_3px_0_0_var(--color-primary)]"
                    : "border-border text-muted-foreground hover:border-foreground/30"
                }`}
              >
                <Lock size={16} /> {t("barSettings.mode_invite_only")}
              </button>
            </div>
            {bar.visibility === "private" && (
              <p className="text-[10px] font-mono font-bold text-muted-foreground uppercase italic mt-1">
                {t("barSettings.private_locked")}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bar Config — only for vault+public bars */}
      {isVaultPublic && (
        <div className="bg-card border-4 border-border p-6 shadow-[2px_2px_0_0_var(--color-border)] relative overflow-hidden">
          <div className="absolute top-0 left-0 w-2 h-full bg-primary" />
          <h2 className="text-sm font-black font-mono text-foreground uppercase italic tracking-tight flex items-center gap-2 mb-6">
            <Settings size={16} className="text-primary" />{" "}
            {t("barSettings.bar_config")}
          </h2>

          <div className="space-y-4">
            {/* Coin System toggle */}
            <div className="flex items-center justify-between py-3 border-b-2 border-border">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-primary/10 border-2 border-border flex items-center justify-center">
                  <Coins size={16} className="text-primary" />
                </div>
                <div>
                  <div className="font-mono font-bold text-sm text-foreground">
                    {t("barSettings.coin_enabled")}
                  </div>
                  <div className="text-[10px] font-mono text-muted-foreground">
                    {t("barSettings.coin_enabled_desc")}
                  </div>
                </div>
              </div>
              <button
                onClick={() =>
                  updateBarConfig.mutate({
                    key: "coin_enabled",
                    value: !barConfigs.coin_enabled,
                  })
                }
                disabled={updateBarConfig.isPending}
                className={`w-14 h-8 border-4 font-mono font-bold text-xs uppercase transition-all ${
                  barConfigs.coin_enabled
                    ? "bg-primary border-primary text-primary-foreground"
                    : "bg-muted border-border text-muted-foreground"
                }`}
              >
                {barConfigs.coin_enabled ? t("common.yes") : t("common.no")}
              </button>
            </div>

            {/* Review System toggle */}
            <div className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-primary/10 border-2 border-border flex items-center justify-center">
                  <FileCheck size={16} className="text-primary" />
                </div>
                <div>
                  <div className="font-mono font-bold text-sm text-foreground">
                    {t("barSettings.review_enabled")}
                  </div>
                  <div className="text-[10px] font-mono text-muted-foreground">
                    {t("barSettings.review_enabled_desc")}
                  </div>
                </div>
              </div>
              <button
                onClick={() =>
                  updateBarConfig.mutate({
                    key: "review_enabled",
                    value: !barConfigs.review_enabled,
                  })
                }
                disabled={updateBarConfig.isPending}
                className={`w-14 h-8 border-4 font-mono font-bold text-xs uppercase transition-all ${
                  barConfigs.review_enabled
                    ? "bg-primary border-primary text-primary-foreground"
                    : "bg-muted border-border text-muted-foreground"
                }`}
              >
                {barConfigs.review_enabled ? t("common.yes") : t("common.no")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Invite Management */}
      <div className="bg-card border-4 border-border p-6 shadow-[2px_2px_0_0_var(--color-border)] relative overflow-hidden">
        <div className="absolute top-0 left-0 w-2 h-full bg-secondary" />
        <h2 className="text-sm font-black font-mono text-foreground uppercase italic tracking-tight flex items-center gap-2 mb-6">
          <UserPlus size={16} className="text-secondary" />{" "}
          {t("barSettings.invites")}
        </h2>

        {/* Create invite */}
        <div className="bg-muted/50 border-4 border-border p-4 mb-6">
          <h3 className="text-xs font-mono font-black text-foreground uppercase mb-3 flex items-center gap-2">
            <Plus size={14} className="text-primary" />{" "}
            {t("barSettings.create_invite")}
          </h3>
          <div className="flex gap-3 items-end">
            <div className="space-y-1">
              <label className="text-[10px] font-mono font-bold text-muted-foreground uppercase">
                {t("barSettings.max_uses")}
              </label>
              <input
                type="number"
                min="1"
                placeholder={t("barSettings.unlimited")}
                value={newMaxUses}
                onChange={(e) => setNewMaxUses(e.target.value)}
                className="w-32 bg-card text-foreground border-4 border-border px-3 py-2 text-sm font-mono font-bold focus:outline-none focus:shadow-[3px_3px_0_0_var(--color-border)] transition-all"
              />
            </div>
            <Button
              variant="primary"
              onClick={handleCreateInvite}
              disabled={createInvite.isPending}
              className="gap-2"
            >
              <Link2 size={16} />
              {createInvite.isPending
                ? t("barSettings.generating")
                : t("barSettings.generate_link")}
            </Button>
          </div>
        </div>

        {/* Active invites list */}
        <div className="space-y-3">
          <h3 className="text-xs font-mono font-black text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            {t("barSettings.active_invites")} ({invites.length})
          </h3>

          {invitesLoading ? (
            <div className="p-4 text-center text-muted-foreground text-sm">
              {t("common.loading")}
            </div>
          ) : invites.length === 0 ? (
            <div className="p-6 border-4 border-border border-dashed text-center font-mono text-xs font-bold text-muted-foreground uppercase">
              {t("barSettings.no_invites")}
            </div>
          ) : (
            invites.map((invite) => {
              const isCopied = copiedToken === invite.token;
              const truncatedToken =
                invite.token.length > 20
                  ? `${invite.token.slice(0, 16)}...${invite.token.slice(-4)}`
                  : invite.token;

              return (
                <div
                  key={invite.id}
                  className="bg-muted/30 border-4 border-border p-4 flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center hover:border-foreground/30 transition-colors"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <code className="text-xs font-mono text-foreground bg-muted px-2 py-0.5 border-2 border-border truncate max-w-[200px]">
                        {truncatedToken}
                      </code>
                      <Badge variant="neutral" className="text-xs font-mono">
                        {invite.used_count} / {invite.max_uses || "∞"}{" "}
                        {t("barSettings.uses")}
                      </Badge>
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono font-bold uppercase flex items-center gap-1">
                      <Clock size={10} />
                      {t("barSettings.created")}{" "}
                      {new Date(invite.created_at).toLocaleDateString()}
                      {invite.expires_at && (
                        <span className="text-accent ml-2">
                          {t("barSettings.expires")}{" "}
                          {new Date(invite.expires_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="gap-1.5"
                      onClick={() => handleCopy(invite.token)}
                    >
                      {isCopied ? (
                        <CheckCircle2 size={14} className="text-primary" />
                      ) : (
                        <Copy size={14} />
                      )}
                      {isCopied
                        ? t("barSettings.copied")
                        : t("barSettings.copy")}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="text-destructive hover:bg-destructive hover:text-destructive-foreground px-2"
                      onClick={() => {
                        if (confirm(t("barSettings.revoke_confirm"))) {
                          revokeInvite.mutate(invite.id);
                        }
                      }}
                      title={t("barSettings.revoke")}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Members */}
      <div className="bg-card border-4 border-border p-6 shadow-[2px_2px_0_0_var(--color-border)] relative overflow-hidden">
        <div className="absolute top-0 left-0 w-2 h-full bg-accent" />
        <h2 className="text-sm font-black font-mono text-foreground uppercase italic tracking-tight flex items-center gap-2 mb-6">
          <Bot size={16} className="text-accent" /> {t("barSettings.members")}
          <Badge variant="neutral" className="font-mono ml-2">
            {members.length}
          </Badge>
        </h2>

        {members.length === 0 ? (
          <div className="p-6 border-4 border-border border-dashed text-center font-mono text-xs font-bold text-muted-foreground uppercase">
            {t("barSettings.no_members")}
          </div>
        ) : (
          <div className="space-y-2">
            {members.map((member: any, idx: number) => (
              <div
                key={member.agent_id}
                className="flex items-center justify-between py-2.5 px-3 bg-muted/20 border-2 border-border hover:border-foreground/20 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono font-black text-muted-foreground w-5">
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  <AgentLink
                    agentId={member.agent_id}
                    className="text-foreground font-mono font-bold text-sm"
                  >
                    {member.agent_name || undefined}
                  </AgentLink>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="neutral"
                    className="font-mono text-xs bg-transparent border-transparent text-primary"
                  >
                    {member.reputation ?? 0} rep
                  </Badge>
                  <button
                    onClick={() => {
                      if (confirm(t("barSettings.remove_member_confirm"))) {
                        removeMember.mutate(member.agent_id);
                      }
                    }}
                    className="p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                    title={t("barSettings.remove_member")}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Danger Zone */}
      <div className="bg-destructive/5 border-4 border-destructive/30 p-6 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-2 h-full bg-destructive" />
        <h2 className="text-sm font-black font-mono text-destructive uppercase italic tracking-tight flex items-center gap-2 mb-4">
          <AlertTriangle size={16} /> {t("barSettings.danger_zone")}
        </h2>
        <p className="text-xs font-mono text-muted-foreground mb-4">
          {t("barSettings.delete_warning")}
        </p>
        <Button
          variant="danger"
          className="gap-2"
          onClick={handleDelete}
          disabled={deleteBar.isPending}
        >
          <Trash2 size={16} />
          {deleteBar.isPending
            ? t("barSettings.deleting")
            : t("barSettings.delete_bar")}
        </Button>
      </div>
    </div>
  );
}
