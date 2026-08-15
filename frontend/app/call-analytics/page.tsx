import type { Metadata } from 'next';
import { CallAnalyticsDashboard } from '@/components/app/call-analytics-dashboard';

export const metadata: Metadata = {
  title: 'Call intelligence | Kisan Sahayak',
  description: 'Privacy-safe outcomes from Kisan Sahayak browser and SIP calls.',
};

export default function CallAnalyticsPage() {
  return <CallAnalyticsDashboard />;
}
