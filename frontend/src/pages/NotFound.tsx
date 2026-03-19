import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Home, Compass } from 'lucide-react';
import { ROUTES } from '@/config/constants';

export default function NotFound() {
  const { t } = useTranslation();

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <Card className="max-w-md w-full p-8 text-center space-y-6">
        <div className="text-6xl font-bold font-display text-muted-foreground/30">404</div>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold font-display text-foreground">
            {t('notFound.title') || 'Page Not Found'}
          </h1>
          <p className="text-muted-foreground text-sm">
            {t('notFound.description') || 'The page you are looking for does not exist or has been moved.'}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
          <Link to={ROUTES.HOME}>
            <Button variant="primary" className="gap-2 w-full sm:w-auto">
              <Home size={16} /> {t('notFound.go_home') || 'Go Home'}
            </Button>
          </Link>
          <Link to={ROUTES.BARS}>
            <Button variant="secondary" className="gap-2 w-full sm:w-auto">
              <Compass size={16} /> {t('notFound.explore_bars') || 'Explore Bars'}
            </Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}