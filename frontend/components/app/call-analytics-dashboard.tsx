'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  CalendarDays,
  ChevronDown,
  Globe2,
  Headphones,
  Info,
  Phone,
  RefreshCw,
  Sprout,
  Waves,
} from 'lucide-react';
import {
  type AnalyticsChannel,
  type AnalyticsDays,
  type AnalyticsFilters,
  type AnalyticsLanguage,
  type AnalyticsOutcome,
  type AnalyticsPayload,
  buildAnalyticsQuery,
} from '@/lib/call-analytics';
import { CallAnalyticsChart } from './call-analytics-chart';
import styles from './call-analytics-dashboard.module.css';

const RESULT_LABELS: Record<string, string> = {
  farming_guidance_delivered: 'Farming guidance delivered',
  live_weather_delivered: 'Live weather delivered',
  expert_request_created: 'Expert request created',
  rain_advisory_delivered: 'Rain advisory delivered',
  no_question: 'No farming question asked',
  caller_ended_early: 'Caller ended early',
  no_response: 'No response',
  tool_failure: 'Live tool unavailable',
  dial_failed: 'Call could not connect',
  not_answered: 'Call not answered',
  recipient_opted_out: 'Future calls stopped',
  agent_error: 'Agent error',
};

const LANGUAGE_LABELS = { en: 'English', hi: 'Hindi', hinglish: 'Hinglish', unknown: 'Unknown' };

function formatDuration(seconds: number) {
  return `${Math.floor(seconds / 60)
    .toString()
    .padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function Select<T extends string | number>({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: T;
  onChange: (value: T) => void;
  children: React.ReactNode;
}) {
  return (
    <label className={styles.selectControl}>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value as T)}>
        {children}
      </select>
    </label>
  );
}

function formatFailureLabel(category: string, fallbackCount: number): string {
  return `${RESULT_LABELS[category] ?? category ?? 'Unknown failure'} · ${fallbackCount}`;
}

export function CallAnalyticsDashboard() {
  const [filters, setFilters] = useState<AnalyticsFilters>({
    days: 7,
    channel: 'all',
    language: 'all',
    outcome: 'all',
  });
  const [data, setData] = useState<AnalyticsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const response = await fetch(`/api/call-analytics?${buildAnalyticsQuery(filters)}`, {
          cache: 'no-store',
          signal,
        });
        if (!response.ok) throw new Error(`Analytics failed with ${response.status}`);
        setData((await response.json()) as AnalyticsPayload);
        setError(null);
      } catch (reason) {
        if ((reason as Error).name !== 'AbortError') {
          setError('Live refresh paused. Showing the most recent successful data.');
        }
      } finally {
        setLoading(false);
      }
    },
    [filters]
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load();
    }, 5000);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [load]);

  const dominantFailure = data?.breakdowns.failures[0];
  const total = data?.summary.total_calls ?? 0;
  const successWidth = total ? ((data?.summary.successful_calls ?? 0) / total) * 100 : 0;
  const updated = useMemo(
    () =>
      data
        ? new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit' }).format(
            new Date(data.generated_at)
          )
        : 'Waiting for data',
    [data]
  );

  const setFilter = <K extends keyof AnalyticsFilters>(key: K, value: AnalyticsFilters[K]) =>
    setFilters((current) => ({ ...current, [key]: value }));

  return (
    <div className={styles.dashboard}>
      <header className={styles.topbar}>
        <Link className={styles.brand} href="/" aria-label="Kisan Sahayak home">
          <span className={styles.brandMark}>
            <Sprout />
          </span>
          <span>Kisan Sahayak</span>
        </Link>
        <div className={styles.headerActions}>
          <Link className={styles.backLink} href="/call-analytics" aria-current="page">
            <BarChart3 aria-hidden="true" />
            Call analytics
          </Link>
          <Link className={styles.backLink} href="/help-requests">
            <Headphones aria-hidden="true" />
            Human requests
          </Link>
          <Link className={styles.backLink} href="/">
            <Waves aria-hidden="true" />
            Voice assistant
          </Link>
        </div>
      </header>

      <main className={styles.main}>
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Day 8 · Outcome reporting</p>
            <h1>Call intelligence</h1>
            <p>See whether every farmer received a useful next step.</p>
          </div>
          <div className={styles.headerUtility}>
            <label className={styles.rangeControl}>
              <CalendarDays />
              <span className="sr-only">Date range</span>
              <select
                value={filters.days}
                onChange={(e) => setFilter('days', Number(e.target.value) as AnalyticsDays)}
              >
                <option value={1}>Today</option>
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
            </label>
            <span className={styles.updated}>
              <i />
              Updated {updated}
            </span>
          </div>
        </header>

        <section className={styles.successDefinition}>
          <Info />
          <p>
            A call is successful when the farmer receives a complete farming or weather answer, a
            live-data result, or a confirmed expert request.
          </p>
        </section>

        {loading && !data ? (
          <div className={styles.skeleton} aria-label="Loading call analytics">
            <span />
            <span />
            <span />
          </div>
        ) : data ? (
          <>
            {error && (
              <div className={styles.errorBanner} role="status">
                {error}
                <button onClick={() => void load()}>
                  <RefreshCw />
                  Retry
                </button>
              </div>
            )}

            <section className={styles.overview} aria-label="Call outcome overview">
              <div className={styles.metricPanel}>
                <span>Successful calls</span>
                <strong>{data.summary.successful_calls.toLocaleString('en-IN')}</strong>
                <p>
                  <b>{data.summary.success_rate}%</b> success rate
                </p>
                <div
                  className={styles.outcomeBar}
                  aria-label={`${data.summary.successful_calls} successful and ${data.summary.failed_calls} failed calls`}
                >
                  <span style={{ width: `${successWidth}%` }} />
                  <i />
                </div>
                <div className={styles.legend}>
                  <span>
                    <i data-tone="success" />
                    Successful
                  </span>
                  <span>
                    <i data-tone="failed" />
                    Failed
                  </span>
                </div>
              </div>

              <div className={styles.metricPanel}>
                <div>
                  <span>Total calls</span>
                  <strong>{data.summary.total_calls.toLocaleString('en-IN')}</strong>
                  <p>
                    Browser {data.breakdowns.channels.browser} · SIP {data.breakdowns.channels.sip}
                  </p>
                </div>
                <div>
                  <span>Failed calls</span>
                  <strong data-tone="failed">
                    {data.summary.failed_calls.toLocaleString('en-IN')}
                  </strong>
                  <p>
                    {dominantFailure
                      ? formatFailureLabel(dominantFailure.category, dominantFailure.count)
                      : 'No failures in this range'}
                  </p>
                </div>
              </div>
            </section>

            <section className={styles.dataCanvas}>
              <div className={styles.canvasHeader}>
                <div>
                  <h2>Outcome over time</h2>
                  <div className={styles.legend}>
                    <span>
                      <i data-tone="success" />
                      Successful
                    </span>
                    <span>
                      <i data-tone="failed" />
                      Failed
                    </span>
                  </div>
                </div>
                <div className={styles.filters}>
                  <Select
                    label="Channel"
                    value={filters.channel}
                    onChange={(v) => setFilter('channel', v as AnalyticsChannel)}
                  >
                    <option value="all">All channels</option>
                    <option value="browser">Browser</option>
                    <option value="sip">SIP</option>
                  </Select>
                  <Select
                    label="Language"
                    value={filters.language}
                    onChange={(v) => setFilter('language', v as AnalyticsLanguage)}
                  >
                    <option value="all">All languages</option>
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="hinglish">Hinglish</option>
                    <option value="unknown">Unknown</option>
                  </Select>
                  <Select
                    label="Outcome"
                    value={filters.outcome}
                    onChange={(v) => setFilter('outcome', v as AnalyticsOutcome)}
                  >
                    <option value="all">All outcomes</option>
                    <option value="successful">Successful</option>
                    <option value="failed">Failed</option>
                  </Select>
                </div>
              </div>

              {total ? (
                <CallAnalyticsChart trend={data.trend} />
              ) : (
                <div className={styles.empty}>
                  <BarChart3 />
                  <h3>Your first completed call will create this chart.</h3>
                  <p>
                    Start a browser or SIP conversation, ask a farming or weather question, and end
                    the call.
                  </p>
                  <Link href="/">Open voice assistant</Link>
                </div>
              )}
            </section>

            <section className={styles.breakdownStrip}>
              <div>
                <span>Channels</span>
                <b>Browser {data.breakdowns.channels.browser}</b>
                <b>SIP {data.breakdowns.channels.sip}</b>
              </div>
              <div>
                <span>Languages</span>
                <b>English {data.breakdowns.languages.en}</b>
                <b>Hindi {data.breakdowns.languages.hi}</b>
                <b>Hinglish {data.breakdowns.languages.hinglish}</b>
              </div>
            </section>

            <section className={styles.ledger}>
              <div className={styles.ledgerHeader}>
                <div>
                  <h2>Recent calls</h2>
                  <p>{data.recent_calls.length} privacy-safe records</p>
                </div>
                <span>
                  <RefreshCw />
                  Refreshes every 5 seconds
                </span>
              </div>
              {data.recent_calls.length ? (
                <div className={styles.rows} role="table" aria-label="Recent call outcomes">
                  <div className={styles.rowHead} role="row">
                    <span>Date &amp; time</span>
                    <span>Channel</span>
                    <span>Language</span>
                    <span>Duration</span>
                    <span>Outcome</span>
                    <span>Result</span>
                    <span aria-hidden="true" />
                  </div>
                  {data.recent_calls.map((call) => (
                    <div className={styles.row} role="row" key={call.call_id}>
                      <span>{formatDate(call.ended_at)}</span>
                      <span>
                        {call.channel === 'browser' ? <Globe2 /> : <Phone />}
                        {call.channel === 'browser' ? 'Browser' : 'SIP'}
                      </span>
                      <span>{LANGUAGE_LABELS[call.language]}</span>
                      <span>{formatDuration(call.duration_seconds)}</span>
                      <span data-outcome={call.outcome}>
                        <i />
                        {call.outcome === 'successful' ? 'Successful' : 'Failed'}
                      </span>
                      <span>
                        {RESULT_LABELS[
                          call.result_category ?? call.failure_category ?? 'agent_error'
                        ] ?? 'Unknown outcome'}
                      </span>
                      <span className={styles.moreAction} aria-hidden="true">
                        <ChevronDown />
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className={styles.noRows}>No completed calls match these filters.</p>
              )}
            </section>
          </>
        ) : (
          <div className={styles.empty}>
            <h3>Call analytics are unavailable.</h3>
            <button onClick={() => void load()}>Try again</button>
          </div>
        )}
      </main>
    </div>
  );
}
