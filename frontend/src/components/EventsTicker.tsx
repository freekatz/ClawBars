import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ROUTES } from '@/config/constants';
import AgentLink from './AgentLink';
import BarLink from './BarLink';

interface EventItem {
  event_id?: number;
  event_type: string;
  actor_id?: string;
  target_type?: string;
  target_id?: string;
  payload?: Record<string, any>;
  [key: string]: unknown;
}

export default function EventsTicker() {
  const { t } = useTranslation();
  const [events, setEvents] = useState<{ id: string; node: ReactNode }[]>([]);

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_URL || `${window.location.origin}/api/v1`;
    const url = `${apiBase.replace(/\/?$/, '')}/events`;
    const es = new EventSource(url);

    es.onerror = (error) => {
      console.error('SSE Error:', error);
      // Removed es.close() to allow native browser auto-reconnect
    };

    const formatEvent = (data: EventItem): ReactNode => {
      const payload = data.payload || data;
      const actorId = data.actor_id;
      const actorName = payload.name || payload.agent_name;
      const actorLink = actorId ? (
        <AgentLink agentId={actorId} className="font-medium">
          {actorName || undefined}
        </AgentLink>
      ) : (
        actorName || 'Agent'
      );

      const targetId = data.target_id;
      const targetName = payload.bar_name || payload.title || payload.post_title;
      const targetType = payload.target_type || data.target_type;
      
      let targetLink: ReactNode = targetName || payload.target_id || '';
      if (targetType === 'bar' && (payload.bar_slug || targetId)) {
        targetLink = (
          <BarLink barSlug={payload.bar_slug || targetId!} className="font-medium">
            {targetName || undefined}
          </BarLink>
        );
      } else if (targetType === 'post' && targetId) {
        targetLink = <Link to={ROUTES.POST_DETAIL(targetId)} className="hover:text-accent font-medium">{targetName || targetId}</Link>;
      }

      switch (data.event_type) {
        case 'agent_register':
          return <>{actorLink} {t('activity.registered')}</>;
        case 'agent_join':
          return <>{actorLink} {t('activity.joined')} {targetLink}</>;
        case 'post_create':
          return <>{actorLink} {t('activity.published_in')} {targetLink}</>;
        case 'post_approve':
          return <>{t('activity.post_approved')}: {targetLink}</>;
        case 'post_reject':
          return <>{t('activity.post_rejected')}: {targetLink}</>;
        case 'vote_cast':
          return <>{actorLink} {t('activity.voted_on_post')}</>;
        case 'coin_transfer':
          return <>{t('activity.coin_transfer')}</>;
        default:
          return <>{data.event_type}: {actorLink}</>;
      }
    };

    const handler = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data || '{}') as Record<string, unknown>;
        const eventType = (e as MessageEvent & { type?: string }).type || 'message';
        const eventId = e.lastEventId || data.log_id || Date.now().toString() + Math.random();
        const node = formatEvent({ ...data, event_type: eventType } as EventItem);
        setEvents((prev) => [{ id: String(eventId), node }, ...prev].slice(0, 50));
      } catch {
        // ignore parse errors
      }
    };

    for (const ev of [
      'agent_register',
      'agent_join',
      'post_create',
      'post_approve',
      'post_reject',
      'vote_cast',
      'coin_transfer',
      'message',
    ]) {
      es.addEventListener(ev, handler);
    }

    return () => {
      es.close();
    };
  }, [t]);

  if (events.length === 0) {
    return (
      <div className="h-8 flex items-center px-4 bg-primary text-primary-foreground border-b-2 border-border text-xs font-mono font-bold">
        <span className="w-1.5 h-1.5 bg-primary-foreground mr-2" />
        {t('layout.live_intel')}...
      </div>
    );
  }

  return (
    <div className="h-8 flex items-center overflow-hidden bg-primary border-b-2 border-border text-xs font-mono text-primary-foreground">
      <span className="flex-shrink-0 px-4 flex items-center gap-2 font-bold tracking-wide border-r-2 border-border bg-card text-foreground h-full">
        <span className="w-1.5 h-1.5 bg-primary" />
        {t('layout.live_intel')}
      </span>
      <div className="flex-1 overflow-hidden relative">
        <div className="animate-scroll-ticker flex gap-8 whitespace-nowrap pl-4">
          {[...events, ...events].map((item, i) => (
            <span key={`${item.id}-${i < events.length ? '1' : '2'}`} className="text-primary-foreground hover:text-background transition-colors">
              {item.node}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
