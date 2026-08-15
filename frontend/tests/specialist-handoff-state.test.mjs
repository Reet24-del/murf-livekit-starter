import assert from 'node:assert/strict';
import test from 'node:test';
import {
  deriveSpecialistPhase,
  getSpecialistVoiceContent,
  parseSpecialistSignal,
} from '../components/app/voice-portal/specialist-handoff-state.mjs';

const agentMessage = (id, message) => ({
  id,
  message,
  from: { isLocal: false },
});

test('shows a connecting state as soon as the handoff is announced', () => {
  const phase = deriveSpecialistPhase([
    agentMessage('1', 'I will connect you to our crop problem specialist.'),
  ]);

  assert.equal(phase, 'connecting');
  assert.equal(
    getSpecialistVoiceContent(phase, 'speaking').label,
    'Connecting you to the specialist'
  );
});

test('shows the specialist as active after its first transferred reply', () => {
  const phase = deriveSpecialistPhase([
    agentMessage('1', 'Main aapko hamari crop problem specialist se connect kar rahi hoon.'),
    agentMessage('2', 'I am your Crop Problem Specialist. Black spots can have several causes.'),
  ]);

  assert.equal(phase, 'active');
  assert.equal(getSpecialistVoiceContent(phase, 'speaking').label, 'Crop specialist is speaking');
  assert.equal(getSpecialistVoiceContent(phase, 'listening').label, 'Crop specialist is listening');
});

test('normal conversations stay on the main-agent UI', () => {
  const phase = deriveSpecialistPhase([
    agentMessage('1', 'The live temperature in Lucknow is 29 degrees Celsius.'),
  ]);

  assert.equal(phase, 'idle');
  assert.equal(getSpecialistVoiceContent(phase, 'speaking'), null);
});

test('uses an explicit backend signal when the spoken announcement is absent', () => {
  const signal = parseSpecialistSignal('{"type":"specialist_handoff","phase":"active"}');

  assert.equal(signal, 'active');
  assert.equal(deriveSpecialistPhase([], signal), 'active');
  assert.equal(getSpecialistVoiceContent(signal, 'speaking').label, 'Crop specialist is speaking');
});

test('ignores malformed and unrelated backend signals', () => {
  assert.equal(parseSpecialistSignal('not json'), null);
  assert.equal(parseSpecialistSignal('{"type":"weather","phase":"active"}'), null);
  assert.equal(parseSpecialistSignal('{"type":"specialist_handoff","phase":"unknown"}'), null);
});
