import { normalizeAudioPlaybackVolume } from './lib/audio-playback-values.mjs';

export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;
  audioPlaybackVolume?: number;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorDark?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;

  // agent dispatch configuration
  agentName?: string;

  // LiveKit Cloud Sandbox configuration
  sandboxId?: string;
}

const safeAgentVolume = normalizeAudioPlaybackVolume(process.env.NEXT_PUBLIC_AGENT_VOLUME);

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'Kisan Sahayak',
  pageTitle: 'Kisan Sahayak — Farm Voice Assistant',
  pageDescription:
    'A voice assistant for crop management, soil health, and weather advisories for Indian farmers.',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/sprout-logo.svg',
  accent: '#7FB35C',
  logoDark: '/sprout-logo.svg',
  accentDark: '#7FB35C',
  startButtonText: 'Start Call',

  // agent dispatch configuration
  agentName: process.env.AGENT_NAME ?? 'kisan-sahayak-primary',

  // LiveKit Cloud Sandbox configuration
  sandboxId: undefined,

  audioPlaybackVolume: safeAgentVolume,
};
