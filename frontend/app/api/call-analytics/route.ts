import { NextResponse } from 'next/server';
import {
  ANALYTICS_CHANNELS,
  ANALYTICS_DAYS,
  ANALYTICS_LANGUAGES,
  ANALYTICS_OUTCOMES,
  type AnalyticsChannel,
  type AnalyticsDays,
  type AnalyticsLanguage,
  type AnalyticsOutcome,
} from '@/lib/call-analytics';
import { getCallAnalytics } from '@/lib/call-analytics-server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams;
  const days = Number(query.get('days') ?? '7');
  const channel = query.get('channel') ?? 'all';
  const language = query.get('language') ?? 'all';
  const outcome = query.get('outcome') ?? 'all';
  if (
    !ANALYTICS_DAYS.includes(days as AnalyticsDays) ||
    !ANALYTICS_CHANNELS.includes(channel as AnalyticsChannel) ||
    !ANALYTICS_LANGUAGES.includes(language as AnalyticsLanguage) ||
    !ANALYTICS_OUTCOMES.includes(outcome as AnalyticsOutcome)
  ) {
    return NextResponse.json({ error: 'Invalid analytics filter.' }, { status: 400 });
  }
  try {
    const payload = await getCallAnalytics({
      days: days as AnalyticsDays,
      channel: channel as AnalyticsChannel,
      language: language as AnalyticsLanguage,
      outcome: outcome as AnalyticsOutcome,
    });
    return NextResponse.json(payload, { headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return NextResponse.json(
      { error: 'Call analytics are unavailable right now.' },
      { status: 500 }
    );
  }
}
