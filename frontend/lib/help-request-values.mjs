export const HELP_REQUEST_STATUSES = Object.freeze(['open', 'in_progress', 'resolved']);

export const HELP_REQUEST_URGENCIES = Object.freeze(['high', 'medium']);

export const HELP_REQUEST_STATUS_LABELS = Object.freeze({
  open: 'Open',
  in_progress: 'In progress',
  resolved: 'Resolved',
});

export const HELP_REQUEST_URGENCY_LABELS = Object.freeze({
  high: 'High',
  medium: 'Medium',
});

export function isHelpRequestStatus(value) {
  return typeof value === 'string' && HELP_REQUEST_STATUSES.includes(value);
}

export function isHelpRequestUrgency(value) {
  return typeof value === 'string' && HELP_REQUEST_URGENCIES.includes(value);
}
