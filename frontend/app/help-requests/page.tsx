import type { Metadata } from 'next';
import { HelpRequestsDashboard } from '@/components/app/help-requests-dashboard';

export const metadata: Metadata = {
  title: 'Human help requests | Kisan Sahayak',
  description: 'Review consented Kisan Sahayak human-help requests.',
};

export default function HelpRequestsPage() {
  return <HelpRequestsDashboard />;
}
