import assert from 'node:assert/strict';
import test from 'node:test';
import {
  HELP_REQUEST_STATUS_LABELS,
  HELP_REQUEST_URGENCY_LABELS,
  isHelpRequestStatus,
  isHelpRequestUrgency,
} from '../lib/help-request-values.mjs';

test('status validation accepts only dashboard workflow values', () => {
  assert.equal(isHelpRequestStatus('open'), true);
  assert.equal(isHelpRequestStatus('in_progress'), true);
  assert.equal(isHelpRequestStatus('resolved'), true);
  assert.equal(isHelpRequestStatus('closed'), false);
  assert.equal(isHelpRequestStatus(null), false);
});

test('urgency validation accepts only Day 7 priorities', () => {
  assert.equal(isHelpRequestUrgency('high'), true);
  assert.equal(isHelpRequestUrgency('medium'), true);
  assert.equal(isHelpRequestUrgency('low'), false);
  assert.equal(isHelpRequestUrgency(undefined), false);
});

test('labels stay readable for the operational dashboard', () => {
  assert.deepEqual(HELP_REQUEST_STATUS_LABELS, {
    open: 'Open',
    in_progress: 'In progress',
    resolved: 'Resolved',
  });
  assert.deepEqual(HELP_REQUEST_URGENCY_LABELS, {
    high: 'High',
    medium: 'Medium',
  });
});
