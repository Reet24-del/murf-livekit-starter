export type SpecialistPhase = 'idle' | 'connecting' | 'active';

export interface SpecialistMessage {
  message?: string;
  from?: { isLocal?: boolean };
}

export interface SpecialistVoiceContent {
  label: string;
  hindiLabel: string;
  hint: string;
}

export declare const SPECIALIST_SIGNAL_TOPIC: 'kisan.sahayak.agent';

export function parseSpecialistSignal(payload: string): Exclude<SpecialistPhase, 'idle'> | null;

export function deriveSpecialistPhase(
  messages: readonly SpecialistMessage[],
  signaledPhase?: Exclude<SpecialistPhase, 'idle'> | null
): SpecialistPhase;

export function getSpecialistVoiceContent(
  phase: SpecialistPhase,
  voiceState: 'ready' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'ended'
): SpecialistVoiceContent | null;
