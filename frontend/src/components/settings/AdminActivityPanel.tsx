import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Activity } from "lucide-react";
import { api } from "@/lib/api";

const EVENT_COLORS: Record<string, string> = {
  post_created: "bg-primary",
  post_approved: "bg-success",
  post_rejected: "bg-destructive",
  agent_registered: "bg-secondary",
  vote_cast: "bg-accent",
  bar_created: "bg-primary",
  coin_granted: "bg-success",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "<1m";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  return `${days}d`;
}

export default function AdminActivityPanel() {
  const { t } = useTranslation();

  const { data: activityData, isLoading } = useQuery({
    queryKey: ["admin-activity"],
    queryFn: () =>
      api
        .get<{ data: any[] }>("/admin/activity-log?limit=10")
        .then((res) => res.data || []),
    refetchInterval: 30000,
  });

  const logs = Array.isArray(activityData) ? activityData : [];

  return (
    <div className="bg-card border-2 border-border p-4 shadow-[2px_2px_0_0_var(--color-border)]">
      <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-accent mb-4 flex items-center gap-1.5">
        <span className="w-2 h-2 bg-accent rotate-45 inline-block" />
        <Activity size={14} />
        {t("settings.admin_activity")}
      </h3>

      {isLoading ? (
        <div className="text-muted-foreground text-sm py-4 font-mono">
          {t("common.loading")}
        </div>
      ) : logs.length === 0 ? (
        <div className="text-muted-foreground text-sm py-4 font-mono">
          {t("settings.no_activity")}
        </div>
      ) : (
        <div className="space-y-0 max-h-96 overflow-y-auto custom-scrollbar border-l-2 border-border ml-2">
          {logs.map((log: any) => (
            <div
              key={log.id}
              className="flex items-start gap-3 pl-4 py-2 relative hover:bg-foreground/5 transition-colors"
            >
              {/* Timeline dot */}
              <div
                className={`absolute left-[-5px] top-3.5 w-2 h-2 border border-border ${EVENT_COLORS[log.event_type] || "bg-muted"}`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-0.5">
                  <span className="text-[9px] font-black font-mono px-1.5 py-0.5 border border-border uppercase bg-muted">
                    {log.event_type}
                  </span>
                  <span className="text-[9px] font-mono text-muted-foreground">
                    {timeAgo(log.created_at)}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-muted-foreground flex flex-wrap gap-x-3">
                  {log.actor_id && (
                    <span>
                      {t("settings.actor")}: {log.actor_id.slice(0, 8)}
                    </span>
                  )}
                  {log.target_type && (
                    <span>
                      {log.target_type}: {log.target_id?.slice(0, 8)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
