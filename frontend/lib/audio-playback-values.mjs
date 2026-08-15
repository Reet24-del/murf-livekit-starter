export function normalizeAudioPlaybackVolume(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return 1;
  return Math.min(Math.max(numericValue, 0), 1);
}
