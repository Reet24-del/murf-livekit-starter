import {
  isHelpRequestStatus as isRuntimeStatus,
  isHelpRequestUrgency as isRuntimeUrgency,
  HELP_REQUEST_STATUS_LABELS as runtimeStatusLabels,
  HELP_REQUEST_STATUSES as runtimeStatuses,
  HELP_REQUEST_URGENCIES as runtimeUrgencies,
  HELP_REQUEST_URGENCY_LABELS as runtimeUrgencyLabels,
} from './help-request-values.mjs';

export type HelpRequestStatus = 'open' | 'in_progress' | 'resolved';
export type HelpRequestUrgency = 'high' | 'medium';

export const HELP_REQUEST_STATUSES = runtimeStatuses as readonly HelpRequestStatus[];
export const HELP_REQUEST_URGENCIES = runtimeUrgencies as readonly HelpRequestUrgency[];
export const HELP_REQUEST_STATUS_LABELS = runtimeStatusLabels as Readonly<
  Record<HelpRequestStatus, string>
>;
export const HELP_REQUEST_URGENCY_LABELS = runtimeUrgencyLabels as Readonly<
  Record<HelpRequestUrgency, string>
>;

export function isHelpRequestStatus(value: unknown): value is HelpRequestStatus {
  return isRuntimeStatus(value);
}

export function isHelpRequestUrgency(value: unknown): value is HelpRequestUrgency {
  return isRuntimeUrgency(value);
}

export type HelpRequestReason = 'serious_crop_problem' | 'market_data_unavailable';
export type HelpRequestLanguage = 'en' | 'hi' | 'hinglish';

export interface HelpRequest {
  reference_id: string;
  caller_id: string;
  caller_name: string | null;
  reason: HelpRequestReason;
  summary: string;
  checks_performed: string;
  urgency: HelpRequestUrgency;
  language: HelpRequestLanguage;
  follow_up_method: 'in_app';
  status: HelpRequestStatus;
  created_at: string;
  updated_at: string;
}
