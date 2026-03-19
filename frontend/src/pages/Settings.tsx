import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Settings as SettingsIcon,
  Sun,
  Moon,
  Monitor,
  Edit3,
  Check,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTheme } from "@/contexts/ThemeContext";
import { useAuth } from "@/contexts/AuthContext";
import { PageHeader } from "@/components/ui/PageHeader";
import AdminUsersPanel from "@/components/settings/AdminUsersPanel";
import AdminAgentsPanel from "@/components/settings/AdminAgentsPanel";
import AdminActivityPanel from "@/components/settings/AdminActivityPanel";

export default function Settings() {
  const { t, i18n } = useTranslation();
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const queryClient = useQueryClient();

  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");

  const { data: configs } = useQuery({
    queryKey: ["configs"],
    queryFn: () =>
      api
        .get<{
          data: Record<string, unknown>;
        }>("/admin/configs")
        .then((res) => res.data || {}),
    enabled: isAdmin,
  });

  const updateConfig = useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) =>
      api.put(`/admin/configs/${key}`, { value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configs"] });
      setEditingKey(null);
    },
  });

  const getConfigLabel = (key: string) => {
    const path = `settings.config_labels.${key}`;
    const translated = t(path);
    return translated !== path ? translated : key;
  };

  const entries = configs ? Object.entries(configs) : [];

  const themeButtons = [
    {
      value: "light" as const,
      icon: <Sun size={16} />,
      label: t("settings.theme_light"),
    },
    {
      value: "dark" as const,
      icon: <Moon size={16} />,
      label: t("settings.theme_dark"),
    },
    {
      value: "system" as const,
      icon: <Monitor size={16} />,
      label: t("settings.theme_system"),
    },
  ];

  const langButtons = [
    { value: "zh", label: "中文" },
    { value: "en", label: "English" },
  ];

  const handleSaveConfig = (key: string) => {
    let parsed: unknown = editValue;
    if (editValue === "true") parsed = true;
    else if (editValue === "false") parsed = false;
    else if (editValue !== "" && !isNaN(Number(editValue)))
      parsed = Number(editValue);
    updateConfig.mutate({ key, value: parsed });
  };

  return (
    <div className="space-y-8 pb-12">
      <PageHeader
        title={t("settings.title")}
        badge="System"
        statusText={t("settings.title")}
        icon={<SettingsIcon size={32} strokeWidth={2.5} />}
      />

      {/* Theme */}
      <div className="bg-card border-2 border-border p-4 shadow-[2px_2px_0_0_var(--color-border)]">
        <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground mb-4">
          {t("settings.theme")}
        </h2>
        <div className="flex flex-wrap gap-2">
          {themeButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setTheme(btn.value)}
              className={`flex items-center gap-2 px-4 py-2 border-2 transition-all font-mono text-sm font-bold uppercase ${
                theme === btn.value
                  ? "bg-primary/20 border-primary text-primary shadow-[2px_2px_0_0_var(--color-primary)]"
                  : "border-border text-muted-foreground hover:text-foreground hover:shadow-[2px_2px_0_0_var(--color-border)]"
              }`}
            >
              {btn.icon} {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Language */}
      <div className="bg-card border-2 border-border p-4 shadow-[2px_2px_0_0_var(--color-border)]">
        <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground mb-4">
          {t("settings.language")}
        </h2>
        <div className="flex gap-2">
          {langButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => i18n.changeLanguage(btn.value)}
              className={`px-4 py-2 border-2 transition-all font-mono text-sm font-bold ${
                i18n.language === btn.value
                  ? "bg-primary/20 border-primary text-primary shadow-[2px_2px_0_0_var(--color-primary)]"
                  : "border-border text-muted-foreground hover:text-foreground hover:shadow-[2px_2px_0_0_var(--color-border)]"
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Runtime Config (admin only) */}
      {isAdmin && entries.length > 0 && (
        <div className="bg-card border-2 border-border p-4 shadow-[2px_2px_0_0_var(--color-border)]">
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground mb-4">
            {t("settings.runtime_config")}
          </h2>
          <div className="space-y-0">
            {entries.map(([key, value]) => (
              <div
                key={key}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-3 border-b-2 border-border last:border-0"
              >
                <div className="min-w-0">
                  <div className="font-mono text-sm text-foreground font-bold truncate">
                    {key}
                  </div>
                  <div className="text-[10px] text-muted-foreground mt-0.5 font-mono">
                    {getConfigLabel(key)}
                  </div>
                </div>

                {isAdmin && editingKey === key ? (
                  <div className="flex items-center gap-2 shrink-0">
                    <input
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="w-32 sm:w-40 bg-card text-foreground border-2 border-border px-2 py-1 text-sm font-mono focus:outline-none focus:shadow-[2px_2px_0_0_var(--color-primary)]"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSaveConfig(key);
                        if (e.key === "Escape") setEditingKey(null);
                      }}
                      autoFocus
                    />
                    <button
                      onClick={() => handleSaveConfig(key)}
                      className="p-1.5 bg-primary text-primary-foreground border-2 border-border shadow-[2px_2px_0_0_var(--color-border)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all"
                    >
                      <Check size={12} />
                    </button>
                    <button
                      onClick={() => setEditingKey(null)}
                      className="p-1.5 border-2 border-border text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 font-mono text-sm text-primary shrink-0">
                    {typeof value === "boolean" ? (
                      <span
                        className={
                          value ? "text-success" : "text-muted-foreground"
                        }
                      >
                        {value ? t("common.yes") : t("common.no")}
                      </span>
                    ) : Array.isArray(value) ? (
                      <span>{(value as unknown[]).join(", ")}</span>
                    ) : (
                      <span>{String(value)}</span>
                    )}
                    {isAdmin && (
                      <button
                        onClick={() => {
                          setEditingKey(key);
                          setEditValue(String(value));
                        }}
                        className="p-1 text-muted-foreground hover:text-primary transition-colors"
                      >
                        <Edit3 size={12} />
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Admin-only panels */}
      {isAdmin && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AdminUsersPanel />
            <AdminAgentsPanel />
          </div>
          <AdminActivityPanel />
        </div>
      )}
    </div>
  );
}
