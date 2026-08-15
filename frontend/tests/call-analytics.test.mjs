import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildAnalyticsQuery,
  isAnalyticsChannel,
  isAnalyticsDays,
  isAnalyticsLanguage,
  isAnalyticsOutcome,
} from '../lib/call-analytics-values.mjs';

test('analytics filters reject untrusted arbitrary values', () => {
  assert.equal(isAnalyticsDays('7'), true);
  assert.equal(isAnalyticsDays('365'), false);
  assert.equal(isAnalyticsChannel('browser'), true);
  assert.equal(isAnalyticsChannel('phone:+919999'), false);
  assert.equal(isAnalyticsLanguage('hinglish'), true);
  assert.equal(isAnalyticsLanguage('full transcript'), false);
  assert.equal(isAnalyticsOutcome('successful'), true);
  assert.equal(isAnalyticsOutcome('maybe'), false);
});

test('analytics query includes one coherent filter snapshot', () => {
  assert.equal(
    buildAnalyticsQuery({ days: 30, channel: 'sip', language: 'hi', outcome: 'failed' }),
    'days=30&channel=sip&language=hi&outcome=failed'
  );
});
