import {
  buildAnalyticsQuery as runtimeBuildQuery,
  ANALYTICS_CHANNELS as runtimeChannels,
  ANALYTICS_DAYS as runtimeDays,
  ANALYTICS_LANGUAGES as runtimeLanguages,
  ANALYTICS_OUTCOMES as runtimeOutcomes,
} from './call-analytics-values.mjs';

export type AnalyticsDays = 1 | 7 | 30 | 90;
export type AnalyticsChannel = 'all' | 'browser' | 'sip';
export type AnalyticsLanguage = 'all' | 'en' | 'hi' | 'hinglish' | 'unknown';
export type AnalyticsOutcome = 'all' | 'successful' | 'failed';
export type CallChannel = Exclude<AnalyticsChannel, 'all'>;
export type CallLanguage = Exclude<AnalyticsLanguage, 'all'>;

export const ANALYTICS_DAYS = runtimeDays as readonly AnalyticsDays[];
export const ANALYTICS_CHANNELS = runtimeChannels as readonly AnalyticsChannel[];
export const ANALYTICS_LANGUAGES = runtimeLanguages as readonly AnalyticsLanguage[];
export const ANALYTICS_OUTCOMES = runtimeOutcomes as readonly AnalyticsOutcome[];

export interface AnalyticsFilters {
  days: AnalyticsDays;
  channel: AnalyticsChannel;
  language: AnalyticsLanguage;
  outcome: AnalyticsOutcome;
}

export interface AnalyticsPayload {
  summary: {
    total_calls: number;
    successful_calls: number;
    failed_calls: number;
    success_rate: number;
  };
  trend: { date: string; successful: number; failed: number }[];
  breakdowns: {
    channels: Record<CallChannel, number>;
    languages: Record<CallLanguage, number>;
    failures: { category: string; count: number }[];
  };
  recent_calls: {
    call_id: string;
    started_at: string;
    ended_at: string;
    duration_seconds: number;
    channel: CallChannel;
    language: CallLanguage;
    outcome: Exclude<AnalyticsOutcome, 'all'>;
    result_category: string | null;
    failure_category: string | null;
  }[];
  generated_at: string;
}

export function buildAnalyticsQuery(filters: AnalyticsFilters): string {
  return runtimeBuildQuery(filters);
}
