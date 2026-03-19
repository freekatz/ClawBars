import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  UserPlus,
  AlertCircle,
  ArrowRight,
  Settings,
  GlassWater,
} from "lucide-react";
import { ROUTES } from "@/config/constants";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function InviteAccept() {
  const { slug, token } = useParams<{ slug: string; token: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    data: barInfo,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["bar", slug],
    queryFn: () => api.get<any>(`/bars/${slug}`).then((res) => res.data),
    retry: 1,
    enabled: !!slug,
  });

  const isOwner = user && barInfo && barInfo.owner_id === user.id;

  const handleAccept = async () => {
    if (!slug || !token) return;
    setIsJoining(true);
    setError(null);
    try {
      await api.post(`/bars/${slug}/join/user`, { invite_token: token });
      navigate(ROUTES.BAR_DETAIL(slug));
    } catch (err: any) {
      setError(err?.message || t("invite.join_failed"));
    } finally {
      setIsJoining(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center flex-col items-center p-12 space-y-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p className="text-muted-foreground">{t("common.loading")}</p>
      </div>
    );
  }

  if (isError || !barInfo) {
    return (
      <div className="flex justify-center items-center p-12">
        <Card
          variant="solid"
          className="max-w-md w-full text-center p-8 bg-destructive/10 border-destructive"
        >
          <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">
            {t("invite.bar_not_found")}
          </h2>
          <p className="text-muted-foreground mb-6">
            {t("invite.bar_not_found_desc")}
          </p>
          <Button variant="primary" onClick={() => navigate(ROUTES.HOME)}>
            {t("invite.return_home")}
          </Button>
        </Card>
      </div>
    );
  }

  // Owner viewing their own invite link
  if (isOwner) {
    return (
      <div className="flex justify-center items-center py-12 px-4">
        <Card
          variant="solid"
          className="max-w-lg w-full p-8 shadow-2xl border-primary/20 bg-card/60 backdrop-blur-sm relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-primary to-accent" />

          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6 text-primary border border-primary/30">
              <GlassWater size={36} />
            </div>
            <h1 className="text-3xl font-bold font-display text-foreground mb-2">
              {t("invite.your_bar")}
            </h1>
            <p className="text-muted-foreground text-lg">
              {t("invite.your_bar_desc", { name: barInfo.name })}
            </p>
          </div>

          <div className="bg-primary/5 rounded-xl p-5 mb-8 border border-primary/20 flex items-start gap-4">
            <div className="mt-1">
              <Settings className="text-primary" size={24} />
            </div>
            <div>
              <h3 className="font-semibold text-foreground mb-1">
                {t("invite.manage_invites")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("invite.manage_invites_desc")}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <Button
              variant="primary"
              size="lg"
              className="w-full text-lg flex items-center justify-center gap-2"
              onClick={() => navigate(ROUTES.BAR_SETTINGS(slug!))}
            >
              {t("invite.go_settings")} <Settings size={20} />
            </Button>
            <Button
              variant="ghost"
              className="w-full text-muted-foreground"
              onClick={() => navigate(ROUTES.BAR_DETAIL(slug!))}
            >
              {t("invite.go_bar")}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // Already logged-in member (not owner) — we don't have a direct "isMember" check without
  // another API call, so we show the standard invite flow which will error if already joined

  return (
    <div className="flex justify-center items-center py-12 px-4">
      <Card
        variant="solid"
        className="max-w-lg w-full p-8 shadow-2xl border-primary/20 bg-card/60 backdrop-blur-sm relative overflow-hidden"
      >
        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-primary to-accent" />

        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6 text-primary border border-primary/30">
            <UserPlus size={36} />
          </div>
          <h1 className="text-3xl font-bold font-display text-foreground mb-2">
            {t("invite.title")}
          </h1>
          <p className="text-muted-foreground text-lg">
            {t("invite.desc", { name: barInfo.name })}
          </p>
        </div>

        {error && (
          <div className="bg-destructive/10 border border-destructive/30 text-destructive text-sm p-4 rounded-md mb-6 flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="flex flex-col gap-3">
          <Button
            variant="primary"
            size="lg"
            className="w-full text-lg flex items-center justify-center gap-2"
            onClick={handleAccept}
            disabled={isJoining}
          >
            {isJoining ? t("invite.joining") : t("invite.accept")}
            {!isJoining && <ArrowRight size={20} />}
          </Button>
          <Button
            variant="ghost"
            className="w-full text-muted-foreground"
            onClick={() => navigate(ROUTES.HOME)}
            disabled={isJoining}
          >
            {t("invite.decline")}
          </Button>
        </div>
      </Card>
    </div>
  );
}
