'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  ArrowUp,
  Check,
  ChevronDown,
  CircleAlert,
  Clock3,
  Minus,
  MoreVertical,
} from 'lucide-react';
import {
  HELP_REQUEST_STATUS_LABELS,
  HELP_REQUEST_URGENCY_LABELS,
  type HelpRequest,
  type HelpRequestStatus,
  type HelpRequestUrgency,
} from '@/lib/help-requests';
import styles from './help-requests-dashboard.module.css';
import { SproutIcon } from './voice-portal/portal-icons';

type StatusFilter = 'all' | HelpRequestStatus;
type UrgencyFilter = 'all' | HelpRequestUrgency;

const REASON_LABELS = {
  serious_crop_problem: 'Serious crop problem',
  market_data_unavailable: 'Market data unavailable',
} as const;

const LANGUAGE_LABELS = {
  en: 'English',
  hi: 'Hindi',
  hinglish: 'Hinglish',
} as const;

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function UrgencyBadge({ urgency }: { urgency: HelpRequestUrgency }) {
  return (
    <span className={styles.urgency} data-urgency={urgency}>
      {urgency === 'high' ? <ArrowUp aria-hidden="true" /> : <Minus aria-hidden="true" />}
      {HELP_REQUEST_URGENCY_LABELS[urgency]}
    </span>
  );
}

function StatusBadge({ status }: { status: HelpRequestStatus }) {
  return (
    <span className={styles.status} data-status={status}>
      <span aria-hidden="true" />
      {HELP_REQUEST_STATUS_LABELS[status]}
    </span>
  );
}

interface RequestDetailsProps {
  request: HelpRequest;
  updatingReference: string | null;
  onStatusChange: (request: HelpRequest, status: HelpRequestStatus) => void;
}

function RequestDetails({ request, updatingReference, onStatusChange }: RequestDetailsProps) {
  const updating = updatingReference === request.reference_id;
  const checks = request.checks_performed
    .split(/\.(?:\s+|$)/)
    .map((item) => item.trim())
    .filter(Boolean);

  return (
    <div className={styles.details} id={`details-${request.reference_id}`}>
      <div className={styles.detailGrid}>
        <section>
          <h3>Summary</h3>
          <p>{request.summary}</p>
        </section>
        <section>
          <h3>Checks performed</h3>
          <ul>
            {checks.map((check) => (
              <li key={check}>{check}</li>
            ))}
          </ul>
        </section>
        <section>
          <h3>Follow-up</h3>
          <p>In app</p>
        </section>
        <section>
          <h3>Created</h3>
          <p>{formatDate(request.created_at)}</p>
        </section>
      </div>
      <div className={styles.detailActions}>
        {request.status !== 'in_progress' && request.status !== 'resolved' && (
          <button
            className={styles.progressButton}
            type="button"
            disabled={updating}
            onClick={() => onStatusChange(request, 'in_progress')}
          >
            <Clock3 aria-hidden="true" />
            {updating ? 'Updating…' : 'Mark in progress'}
          </button>
        )}
        {request.status !== 'resolved' && (
          <button
            className={styles.resolveButton}
            type="button"
            disabled={updating}
            onClick={() => onStatusChange(request, 'resolved')}
          >
            <Check aria-hidden="true" />
            {updating ? 'Updating…' : 'Resolve'}
          </button>
        )}
        {request.status === 'resolved' && <p className={styles.resolvedNote}>Request resolved</p>}
      </div>
    </div>
  );
}

export function HelpRequestsDashboard() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [urgencyFilter, setUrgencyFilter] = useState<UrgencyFilter>('all');
  const [requests, setRequests] = useState<HelpRequest[]>([]);
  const [selectedReference, setSelectedReference] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingReference, setUpdatingReference] = useState<string | null>(null);
  const selectedReferenceRef = useRef(selectedReference);

  useEffect(() => {
    selectedReferenceRef.current = selectedReference;
  }, [selectedReference]);

  const fetchRequests = useCallback(
    async (signal?: AbortSignal) => {
      const query = new URLSearchParams();
      if (statusFilter !== 'all') query.set('status', statusFilter);
      if (urgencyFilter !== 'all') query.set('urgency', urgencyFilter);

      try {
        const response = await fetch(`/api/help-requests?${query.toString()}`, {
          cache: 'no-store',
          signal,
        });
        if (!response.ok) throw new Error(`Request failed with ${response.status}`);
        const payload = (await response.json()) as { requests: HelpRequest[] };
        setRequests(payload.requests);
        setError(null);
        const currentSelection = selectedReferenceRef.current;
        if (
          payload.requests.length > 0 &&
          !payload.requests.some((item) => item.reference_id === currentSelection)
        ) {
          setSelectedReference(payload.requests[0].reference_id);
        }
        if (payload.requests.length === 0) setSelectedReference(null);
      } catch (fetchError) {
        if ((fetchError as Error).name !== 'AbortError') {
          setError('Could not refresh help requests. The last successful list is still shown.');
        }
      } finally {
        setLoading(false);
      }
    },
    [statusFilter, urgencyFilter]
  );

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    void fetchRequests(controller.signal);

    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') void fetchRequests();
    }, 3000);

    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [fetchRequests]);

  const counts = useMemo(
    () => ({
      open: requests.filter((request) => request.status === 'open').length,
      inProgress: requests.filter((request) => request.status === 'in_progress').length,
      resolved: requests.filter((request) => request.status === 'resolved').length,
    }),
    [requests]
  );

  const updateStatus = async (request: HelpRequest, status: HelpRequestStatus) => {
    setUpdatingReference(request.reference_id);
    try {
      const response = await fetch(`/api/help-requests/${request.reference_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) throw new Error(`Update failed with ${response.status}`);
      const payload = (await response.json()) as { request: HelpRequest };
      setRequests((current) =>
        current.map((item) =>
          item.reference_id === payload.request.reference_id ? payload.request : item
        )
      );
      setError(null);
      await fetchRequests();
    } catch {
      setError('Status could not be updated. Please try again.');
    } finally {
      setUpdatingReference(null);
    }
  };

  return (
    <div className={styles.dashboard}>
      <header className={styles.topbar}>
        <Link className={styles.brand} href="/" aria-label="Kisan Sahayak home">
          <span className={styles.brandMark}>
            <SproutIcon aria-hidden="true" />
          </span>
          <span>Kisan Sahayak</span>
        </Link>
        <Link className={styles.backLink} href="/">
          <ArrowLeft aria-hidden="true" />
          Back to voice assistant
        </Link>
      </header>

      <main className={styles.main}>
        <div className={styles.intro}>
          <h1>Human help requests</h1>
          <p aria-live="polite">
            {requests.length} {requests.length === 1 ? 'request' : 'requests'}
            <span aria-hidden="true"> • </span>
            <strong>{counts.open} open</strong>
            <span aria-hidden="true"> • </span>
            <em>{counts.inProgress} in progress</em>
            <span aria-hidden="true"> • </span>
            {counts.resolved} resolved
          </p>
        </div>

        <div className={styles.filters} aria-label="Help request filters">
          <label>
            <span>Status</span>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            >
              <option value="all">All statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In progress</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>
          <label>
            <span>Urgency</span>
            <select
              value={urgencyFilter}
              onChange={(event) => setUrgencyFilter(event.target.value as UrgencyFilter)}
            >
              <option value="all">All urgency</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
            </select>
          </label>
        </div>

        {error && (
          <div className={styles.errorBanner} role="alert">
            <CircleAlert aria-hidden="true" />
            <span>{error}</span>
            <button type="button" onClick={() => void fetchRequests()}>
              Retry
            </button>
          </div>
        )}

        <section
          className={styles.requestSurface}
          aria-label="Human help request log"
          aria-busy={loading || updatingReference !== null}
        >
          <div className={styles.tableHeader} aria-hidden="true">
            <span>Reference</span>
            <span>Farmer</span>
            <span>Reason</span>
            <span>Urgency</span>
            <span>Language</span>
            <span>Status</span>
            <span>Updated</span>
            <span aria-hidden="true" />
          </div>

          {loading && requests.length === 0 && (
            <p className={styles.emptyState}>Loading help requests…</p>
          )}
          {!loading && requests.length === 0 && (
            <div className={styles.emptyState}>
              <Check aria-hidden="true" />
              <div>
                <strong>No matching requests</strong>
                <p>New consented requests will appear here automatically.</p>
              </div>
            </div>
          )}

          {requests.map((request) => {
            const expanded = selectedReference === request.reference_id;
            return (
              <article
                className={styles.request}
                data-expanded={expanded}
                key={request.reference_id}
              >
                <button
                  className={styles.requestRow}
                  type="button"
                  aria-expanded={expanded}
                  aria-controls={`details-${request.reference_id}`}
                  onClick={() => setSelectedReference(expanded ? null : request.reference_id)}
                >
                  <span className={styles.reference} data-label="Reference">
                    <ChevronDown aria-hidden="true" />
                    {request.reference_id}
                  </span>
                  <span data-label="Farmer">{request.caller_name || 'Unknown caller'}</span>
                  <span data-label="Reason">{REASON_LABELS[request.reason]}</span>
                  <span data-label="Urgency">
                    <UrgencyBadge urgency={request.urgency} />
                  </span>
                  <span data-label="Language">{LANGUAGE_LABELS[request.language]}</span>
                  <span className={styles.mobileStatus} data-label="Status">
                    <StatusBadge status={request.status} />
                  </span>
                  <span data-label="Updated">{formatDate(request.updated_at)}</span>
                  <span className={styles.moreAction} aria-hidden="true">
                    <MoreVertical />
                  </span>
                </button>
                {expanded && (
                  <RequestDetails
                    request={request}
                    updatingReference={updatingReference}
                    onStatusChange={updateStatus}
                  />
                )}
              </article>
            );
          })}
        </section>

        <p className={styles.resultCount}>
          Showing {requests.length} {requests.length === 1 ? 'request' : 'requests'}
        </p>
      </main>
    </div>
  );
}
