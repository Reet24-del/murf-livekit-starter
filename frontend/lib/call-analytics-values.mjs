export const ANALYTICS_DAYS = [1, 7, 30, 90];
export const ANALYTICS_CHANNELS = ['all', 'browser', 'sip'];
export const ANALYTICS_LANGUAGES = ['all', 'en', 'hi', 'hinglish', 'unknown'];
export const ANALYTICS_OUTCOMES = ['all', 'successful', 'failed'];

export function isAnalyticsDays(value) {
  return ANALYTICS_DAYS.includes(Number(value));
}

export function isAnalyticsChannel(value) {
  return ANALYTICS_CHANNELS.includes(value);
}

export function isAnalyticsLanguage(value) {
  return ANALYTICS_LANGUAGES.includes(value);
}

export function isAnalyticsOutcome(value) {
  return ANALYTICS_OUTCOMES.includes(value);
}

export function buildAnalyticsQuery(filters) {
  const query = new URLSearchParams();
  query.set('days', String(filters.days));
  query.set('channel', filters.channel);
  query.set('language', filters.language);
  query.set('outcome', filters.outcome);
  return query.toString();
}
