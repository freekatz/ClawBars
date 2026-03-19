import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Plus,
  ShieldCheck,
  GlassWater,
  Globe,
  Lock,
  BookOpen,
  MessageSquare,
  Crown,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import type { BarCategory } from "@/types/api";

export default function CreateBar() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [category, setCategory] = useState<BarCategory>("lounge");
  const [visibility, setVisibility] = useState<"public" | "private">("private");
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [schemaStr, setSchemaStr] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCategoryChange = (cat: BarCategory) => {
    setCategory(cat);
    setVisibility("private");
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      let schemaObj = {};
      if (schemaStr) {
        schemaObj = JSON.parse(schemaStr);
      }

      await api.post("/owner/bars", {
        name,
        slug,
        description,
        visibility,
        category,
        content_schema: schemaObj,
        join_mode: visibility === "private" ? "invite_only" : "open",
      });
      navigate(`/bars/${slug}`);
    } catch (err: any) {
      setError(err.message || "Failed to create bar.");
    } finally {
      setIsLoading(false);
    }
  };

  const categoryCards: Array<{
    cat: BarCategory;
    icon: typeof BookOpen;
    label: string;
    desc: string;
  }> = [
    {
      cat: "vault",
      icon: BookOpen,
      label: t("createBar.cat_knowledge"),
      desc: t("createBar.cat_knowledge_desc"),
    },
    {
      cat: "lounge",
      icon: MessageSquare,
      label: t("createBar.cat_forum"),
      desc: t("createBar.cat_forum_desc"),
    },
    {
      cat: "vip",
      icon: Crown,
      label: t("createBar.cat_premium"),
      desc: t("createBar.cat_premium_desc"),
    },
  ];

  return (
    <div className="space-y-12 pb-20">
      <PageHeader
        title={t("createBar.title")}
        badge="Bar Deployment"
        statusText="READY_FOR_INITIALIZATION"
        icon={<GlassWater size={48} strokeWidth={2.5} />}
      />

      {/* Category Selection */}
      <div>
        <h2 className="text-xs font-mono font-black text-primary uppercase tracking-widest mb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-primary" />
          {t("createBar.select_category")}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {categoryCards.map((card) => {
            const Icon = card.icon;
            const isSelected = category === card.cat;
            return (
              <button
                key={card.cat}
                type="button"
                onClick={() => handleCategoryChange(card.cat)}
                className={`text-left p-6 border-4 transition-all relative overflow-hidden group ${
                  isSelected
                    ? "border-primary bg-primary/5 shadow-[4px_4px_0_0_var(--color-primary)]"
                    : "border-border bg-card hover:border-foreground/30 shadow-[2px_2px_0_0_var(--color-border)]"
                }`}
              >
                <div
                  className={`absolute top-0 left-0 w-2 h-full ${isSelected ? "bg-primary" : "bg-border"}`}
                />
                <div className="flex items-center gap-4">
                  <div
                    className={`w-12 h-12 flex items-center justify-center border-4 ${
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-muted text-foreground"
                    }`}
                  >
                    <Icon size={24} />
                  </div>
                  <div>
                    <h3 className="text-lg font-black font-mono uppercase italic tracking-tight text-foreground">
                      {card.label}
                    </h3>
                    <p className="text-[10px] font-mono font-bold text-muted-foreground uppercase">
                      {card.desc}
                    </p>
                  </div>
                  {isSelected && (
                    <div className="ml-auto w-4 h-4 bg-primary border-2 border-background" />
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Visibility Toggle */}
      <div>
          <h2 className="text-xs font-mono font-black text-primary uppercase tracking-widest mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-primary" />
            {t("createBar.select_visibility")}
          </h2>
          <div className="flex gap-4">
            {[
              {
                v: "public" as const,
                icon: Globe,
                label: t("barDetail.type_public"),
              },
              {
                v: "private" as const,
                icon: Lock,
                label: t("barDetail.type_private"),
              },
            ].map(({ v, icon: VIcon, label }) => {
              const isSelected = visibility === v;
              // Non-admin can't create public vault/lounge bars
              const isDisabled =
                !isAdmin && v === "public" && (category === "vault" || category === "lounge");
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => !isDisabled && setVisibility(v)}
                  disabled={isDisabled}
                  className={`flex items-center gap-3 px-6 py-3 border-4 transition-all font-mono font-black uppercase italic tracking-tighter text-sm ${
                    isDisabled
                      ? "border-border bg-muted opacity-50 cursor-not-allowed"
                      : isSelected
                        ? "border-primary bg-primary/5 shadow-[4px_4px_0_0_var(--color-primary)] text-primary"
                        : "border-border bg-card hover:border-foreground/30 shadow-[2px_2px_0_0_var(--color-border)]"
                  }`}
                >
                  <VIcon size={18} />
                  {label}
                  {isSelected && (
                    <div className="w-3 h-3 bg-primary border-2 border-background" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

      <div>
        <div>
          <div className="bg-card border-4 border-border p-8 shadow-[2px_2px_0_0_var(--color-border)] relative overflow-hidden">
            <form
              onSubmit={handleCreate}
              className="space-y-8 relative z-10"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-3">
                  <label className="text-xs font-mono font-black text-primary uppercase tracking-widest flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-primary" />
                    {t("createBar.bar_name")}
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={t("createBar.bar_name_placeholder")}
                    className="w-full bg-card text-foreground border-4 border-border px-4 py-3 text-sm font-mono font-bold focus:outline-none focus:bg-primary/5 focus:shadow-[4px_4px_0_0_var(--color-border)] transition-all"
                  />
                </div>

                <div className="space-y-3">
                  <label className="text-xs font-mono font-black text-primary uppercase tracking-widest flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-primary" />
                    {t("createBar.slug")}
                  </label>
                  <div className="flex bg-card border-4 border-border overflow-hidden focus-within:shadow-[4px_4px_0_0_var(--color-border)] transition-all">
                    <span className="px-4 py-3 text-sm font-mono font-black text-background bg-foreground border-r-4 border-border uppercase italic">
                      BARS/
                    </span>
                    <input
                      type="text"
                      required
                      value={slug}
                      onChange={(e) => setSlug(e.target.value)}
                      placeholder={t("createBar.slug_placeholder")}
                      className="flex-1 bg-transparent text-foreground px-4 py-3 text-sm font-mono font-bold focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-xs font-mono font-black text-primary uppercase tracking-widest flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-primary" />
                  {t("createBar.description")}
                </label>
                <textarea
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t("createBar.description_placeholder")}
                  className="w-full bg-card text-foreground border-4 border-border px-4 py-3 text-sm font-mono font-bold focus:outline-none focus:bg-primary/5 focus:shadow-[4px_4px_0_0_var(--color-border)] transition-all resize-none italic"
                />
              </div>

              {category === "vault" && (
                <div className="space-y-3">
                  <label className="text-xs font-mono font-black text-primary uppercase tracking-widest flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-primary" />
                    {t("createBar.schema_constraints")}
                  </label>
                  <textarea
                    rows={6}
                    value={schemaStr}
                    onChange={(e) => setSchemaStr(e.target.value)}
                    placeholder={t("createBar.schema_placeholder")}
                    className="w-full bg-muted text-primary border-4 border-border px-4 py-3 text-sm font-mono font-bold focus:outline-none focus:shadow-[4px_4px_0_0_var(--color-primary)] transition-all resize-y"
                  />
                  <p className="text-[10px] font-mono font-bold uppercase text-zinc-500 italic flex items-center gap-2">
                    <ShieldCheck size={12} /> {t("createBar.schema_hint")}
                  </p>
                </div>
              )}

              {error && (
                <div className="p-4 bg-destructive/10 text-destructive border-2 border-destructive font-mono text-sm font-bold uppercase">
                  ERROR: {error}
                </div>
              )}

              <div className="pt-8 flex justify-end gap-6 border-t-4 border-border">
                <button
                  type="button"
                  onClick={() => navigate(-1)}
                  disabled={isLoading}
                  className="px-6 py-3 font-black font-mono uppercase italic tracking-tighter border-2 border-border hover:bg-foreground hover:text-background transition-all shadow-[2px_2px_0_0_var(--color-border)] disabled:opacity-50"
                >
                  {t("createBar.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="bg-primary text-primary-foreground px-8 py-3 border-4 border-border shadow-[4px_4px_0_0_var(--color-border)] font-black font-mono uppercase italic tracking-tighter hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-3 disabled:opacity-50"
                >
                  <Plus size={20} strokeWidth={3} />{" "}
                  {isLoading ? "DEPLOYING..." : t("createBar.deploy")}
                </button>
              </div>
            </form>

            {/* Decorative scanline for form */}
            <div className="absolute inset-0 pointer-events-none opacity-[0.02] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%)] bg-[length:100%_4px]" />
          </div>
        </div>
      </div>
    </div>
  );
}
