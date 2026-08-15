import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizeAudioPlaybackVolume } from '../lib/audio-playback-values.mjs';

test('audio playback volume always stays within the browser-supported range', () => {
  assert.equal(normalizeAudioPlaybackVolume(1.5), 1);
  assert.equal(normalizeAudioPlaybackVolume(-0.2), 0);
  assert.equal(normalizeAudioPlaybackVolume(0.75), 0.75);
  assert.equal(normalizeAudioPlaybackVolume(undefined), 1);
});
