import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ROUTES } from '@/config/constants';
import { api } from '@/lib/api';

interface BarLinkProps {
  barSlug: string;
  className?: string;
  children?: React.ReactNode;
}

export default function BarLink({ barSlug, className = '', children }: BarLinkProps) {
  const { data: bar } = useQuery({
    queryKey: ['bar', barSlug],
    queryFn: () => api.get<{ data: any }>(`/bars/${barSlug}`).then(res => (res.data || {}) as { name?: string }),
    enabled: !children && !!barSlug,
    staleTime: 5 * 60 * 1000,
  });

  const displayName = children || bar?.name || barSlug;

  return (
    <Link
      to={ROUTES.BAR_DETAIL(barSlug)}
      className={`hover:text-amber-400 transition-colors ${className}`}
    >
      {displayName}
    </Link>
  );
}
