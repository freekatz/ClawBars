import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ROUTES } from '@/config/constants';
import { api } from '@/lib/api';

interface AgentLinkProps {
  agentId: string;
  className?: string;
  children?: React.ReactNode;
}

export default function AgentLink({ agentId, className = '', children }: AgentLinkProps) {
  const { data: agent } = useQuery({
    queryKey: ['agent', agentId],
    queryFn: () => api.get<{ data: any }>(`/agents/${agentId}`).then(res => (res.data || {}) as { name?: string }),
    enabled: !children && !!agentId,
    staleTime: 5 * 60 * 1000,
  });

  const displayName = children || agent?.name || agentId;

  return (
    <Link
      to={ROUTES.AGENT_PROFILE(agentId)}
      className={`hover:text-primary transition-colors ${className}`}
    >
      {displayName}
    </Link>
  );
}
