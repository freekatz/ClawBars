import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ROUTES } from "@/config/constants";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";

export default function Auth() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user, isLoading, refetch } = useAuth();
  const [isLogin, setIsLogin] = useState(true);

  useEffect(() => {
    if (!isLoading && user) navigate(ROUTES.HOME, { replace: true });
  }, [user, isLoading, navigate]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const form = e.target as HTMLFormElement;
    const email = (form.elements.namedItem("email") as HTMLInputElement)?.value;
    const password = (form.elements.namedItem("password") as HTMLInputElement)
      ?.value;
    const name = (form.elements.namedItem("name") as HTMLInputElement)?.value;

    try {
      if (isLogin) {
        const res: any = await api.post("/auth/login", { email, password });
        const data = res?.data || res;
        if (data?.access_token) {
          auth.setToken(data.access_token);
          if (data.refresh_token) auth.setRefreshToken(data.refresh_token);
          await refetch();
          navigate(ROUTES.HOME);
        }
      } else {
        const res: any = await api.post("/auth/register", {
          email,
          password,
          name: name || email.split("@")[0],
        });
        // Register returns user profile; user must login to get tokens
        if (res?.data) {
          setIsLogin(true);
          setError(null);
          // Auto-login after register
          const loginRes: any = await api.post("/auth/login", {
            email,
            password,
          });
          const loginData = loginRes?.data || loginRes;
          if (loginData?.access_token) {
            auth.setToken(loginData.access_token);
            if (loginData.refresh_token)
              auth.setRefreshToken(loginData.refresh_token);
            await refetch();
            navigate(ROUTES.HOME);
          }
        }
      }
    } catch (err: any) {
      const code = err?.code;
      const msg = (err?.message || "").toLowerCase();
      if (
        code === 40901 ||
        msg.includes("already") ||
        msg.includes("registered")
      ) {
        setError(t("auth.email_taken"));
      } else if (
        isLogin &&
        (code === 40102 || code === 401 || msg.includes("invalid"))
      ) {
        setError(t("auth.invalid_credentials"));
      } else {
        setError(
          isLogin ? t("auth.invalid_credentials") : t("auth.register_failed"),
        );
      }
    } finally {
      setLoading(false);
    }
  };

  if (isLoading) return null;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-background">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-display font-bold tracking-tight text-foreground">
            {isLogin ? t("auth.login") : t("auth.register")}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground font-mono">
            {isLogin
              ? t("auth.sign_in_prompt")
              : t("auth.create_account_prompt")}
          </p>
        </div>

        <Card
          glowColor="none"
          className="p-8 relative overflow-hidden bg-card border-4 border-black shadow-[8px_8px_0_0_#111111]"
        >
          {/* Flat geometric decorations */}
          <div className="absolute -top-16 -right-16 w-32 h-32 bg-primary/20 border-4 border-primary rounded-full" />
          <div className="absolute -bottom-16 -left-16 w-32 h-32 bg-secondary/20 border-4 border-secondary rotate-45" />

          <div className="relative z-10 flex gap-2 mb-6 p-1 bg-muted rounded-none border-2 border-border">
            <button
              type="button"
              onClick={() => {
                setIsLogin(true);
                setError(null);
              }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                isLogin
                  ? "bg-primary/20 text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t("auth.login")}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsLogin(false);
                setError(null);
              }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                !isLogin
                  ? "bg-primary/20 text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t("auth.register")}
            </button>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            {error && (
              <div className="text-sm text-destructive font-mono py-2 px-3 bg-destructive/10 rounded-md border border-destructive/30">
                {error}
              </div>
            )}
            {!isLogin && (
              <div className="space-y-2">
                <label className="text-xs font-mono text-muted-foreground uppercase">
                  {t("auth.name")}
                </label>
                <input
                  name="name"
                  type="text"
                  required
                  className="input-base"
                  placeholder={t("auth.display_name")}
                />
              </div>
            )}
            <div className="space-y-2">
              <label className="text-xs font-mono text-muted-foreground uppercase">
                {t("auth.email")}
              </label>
              <input
                name="email"
                type="email"
                required
                className="input-base"
                placeholder="your@email.com"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-mono text-muted-foreground uppercase">
                {t("auth.password")}
              </label>
              <input
                name="password"
                type="password"
                required
                minLength={8}
                className="input-base"
                placeholder="••••••••"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full mt-6"
              disabled={loading}
            >
              {loading
                ? t("common.loading")
                : isLogin
                  ? t("auth.sign_in")
                  : t("auth.create_account")}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
