'use client';

import { useEffect, useState } from 'react';
import { ConnectionState } from 'livekit-client';
import { ClipboardList } from 'lucide-react';
import {
  useSessionContext,
  useSessionMessages,
  useTrackVolume,
  useVoiceAssistant,
} from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import {
  type CallerProfileSummary,
  fetchCallerProfile,
  getStoredCallerId,
} from '@/lib/caller-profile';
import { MemoryPanel } from './voice-portal/memory-panel';
import { PhoneIcon, ResetIcon, SproutIcon } from './voice-portal/portal-icons';
import { TranscriptDock } from './voice-portal/transcript-dock';
import { VoiceOrb } from './voice-portal/voice-orb';
import styles from './voice-portal/voice-portal.module.css';
import { VOICE_STATE_CONTENT, type VoiceState } from './voice-portal/voice-state';
import { WeatherPanel } from './voice-portal/weather-panel';

interface KisanSahayakViewProps {
  appConfig: AppConfig;
}

function errorType(error: unknown): 'permission_denied' | 'other' {
  const value = error as Error;
  const message = value?.message?.toLowerCase() || '';
  return value?.name === 'NotAllowedError' || /permission|allowed|denied/.test(message)
    ? 'permission_denied'
    : 'other';
}

export function KisanSahayakView({ appConfig: _appConfig }: KisanSahayakViewProps) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const { state: agentState, audioTrack } = useVoiceAssistant();
  const [transcriptOpen, setTranscriptOpen] = useState(true);
  const [hasConnectedOnce, setHasConnectedOnce] = useState(false);
  const [micError, setMicError] = useState<'permission_denied' | 'other' | null>(null);
  const [micPermissionStatus, setMicPermissionStatus] = useState<PermissionState | 'unknown'>(
    'unknown'
  );
  const [detectedLocation, setDetectedLocation] = useState('Lucknow');
  const [callerProfile, setCallerProfile] = useState<CallerProfileSummary | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  const agentVolume = useTrackVolume(audioTrack, {
    fftSize: 256,
    smoothingTimeConstant: 0.4,
  });
  const userVolume = useTrackVolume(session.local?.microphoneTrack, {
    fftSize: 256,
    smoothingTimeConstant: 0.4,
  });

  useEffect(() => {
    const savedLocation = localStorage.getItem('detected_location')?.split(',')[0];
    if (savedLocation) setDetectedLocation(savedLocation);
  }, []);

  useEffect(() => {
    if (session.isConnected) {
      setHasConnectedOnce(true);
      setTranscriptOpen(true);
    }
  }, [session.isConnected]);

  useEffect(() => {
    if (!navigator.permissions?.query) return;
    let permissionStatus: PermissionStatus | null = null;
    navigator.permissions
      .query({ name: 'microphone' as PermissionName })
      .then((status) => {
        permissionStatus = status;
        setMicPermissionStatus(status.state);
        status.onchange = () => {
          setMicPermissionStatus(status.state);
          if (status.state === 'granted') setMicError(null);
        };
      })
      .catch(() => setMicPermissionStatus('unknown'));
    return () => {
      if (permissionStatus) permissionStatus.onchange = null;
    };
  }, []);

  useEffect(() => {
    const userId = getStoredCallerId();
    if (!userId) {
      setProfileLoading(false);
      return;
    }
    const controller = new AbortController();
    fetchCallerProfile(userId, controller.signal)
      .then(setCallerProfile)
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') console.warn('Profile summary unavailable');
      })
      .finally(() => setProfileLoading(false));
    return () => controller.abort();
  }, []);

  let currentState: VoiceState = 'ready';
  if (
    session.connectionState === ConnectionState.Connecting ||
    session.connectionState === ConnectionState.Reconnecting
  ) {
    currentState = 'connecting';
  } else if (session.isConnected) {
    currentState =
      agentState === 'speaking' ? 'speaking' : agentState === 'thinking' ? 'thinking' : 'listening';
  } else if (hasConnectedOnce) {
    currentState = 'ended';
  }

  const activeState = VOICE_STATE_CONTENT[currentState];
  const hasMicError = micError === 'permission_denied' || micPermissionStatus === 'denied';

  const startSession = async () => {
    try {
      setMicError(null);
      await session.start?.();
    } catch (error: unknown) {
      console.error('Failed to start voice session:', error);
      setMicError(errorType(error));
    }
  };

  const handleStartAgain = async () => {
    setHasConnectedOnce(false);
    await startSession();
  };

  const handleResetMemory = () => {
    if (!window.confirm("Clear this caller's saved profile and conversation memory?")) return;
    const userId = getStoredCallerId();
    if (!userId) {
      window.location.reload();
      return;
    }
    fetch(`/api/profile?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' })
      .then((response) => {
        if (!response.ok) throw new Error(`Memory reset failed with ${response.status}`);
        localStorage.removeItem('user_id');
        window.location.reload();
      })
      .catch((error: unknown) => console.error('Reset profile error:', error));
  };

  return (
    <div className={styles.portal} data-state={currentState}>
      <header className={styles.topbar}>
        <a className={styles.brand} href="/" aria-label="Kisan Sahayak home">
          <span className={styles.brandMark}>
            <SproutIcon aria-hidden="true" />
          </span>
          <span>Kisan Sahayak</span>
        </a>
        <div className={styles.topbarActions}>
          <a className={styles.helpLink} href="/help-requests">
            <ClipboardList aria-hidden="true" />
            <span>Human request log</span>
          </a>
          <span className={styles.connectionState}>
            <span className={styles.connectionDot} data-connected={session.isConnected} />
            {session.isConnected ? 'Connected' : 'Disconnected'}
          </span>
          <span className={styles.headerDivider} aria-hidden="true" />
          <button className={styles.resetButton} type="button" onClick={handleResetMemory}>
            <ResetIcon aria-hidden="true" />
            <span>Reset memory</span>
          </button>
        </div>
      </header>

      <main className={styles.portalGrid}>
        {hasMicError && (
          <aside className={styles.micErrorCard} role="alert">
            <strong>Microphone access is blocked</strong>
            <p>Allow microphone access in your browser settings, then try again.</p>
            <button className={styles.retryButton} type="button" onClick={startSession}>
              Try again
            </button>
          </aside>
        )}

        <WeatherPanel
          temperature="29°C"
          condition="Ask for live weather"
          location={detectedLocation}
          advisory="Live details available by voice"
        />

        <section className={styles.voiceStage} aria-labelledby="voice-state-title">
          <VoiceOrb state={currentState} userVolume={userVolume} agentVolume={agentVolume} />
          <div className={styles.stateCopy}>
            <h1 id="voice-state-title">{activeState.label}</h1>
            <p className={styles.hindiLabel}>{activeState.hindiLabel}</p>
            <p className={styles.stateHint}>{activeState.hint}</p>
          </div>
          <div className={styles.controls}>
            {currentState === 'ready' && (
              <button className={styles.primaryButton} type="button" onClick={startSession}>
                <PhoneIcon aria-hidden="true" />
                <span>Start Call / बातचीत शुरू करें</span>
              </button>
            )}
            {currentState === 'ended' && (
              <button className={styles.primaryButton} type="button" onClick={handleStartAgain}>
                <PhoneIcon aria-hidden="true" />
                <span>Start Again / फिर से शुरू करें</span>
              </button>
            )}
            {session.isConnected && (
              <button className={styles.dangerButton} type="button" onClick={() => session.end?.()}>
                <PhoneIcon aria-hidden="true" />
                <span>End Call / कॉल समाप्त करें</span>
              </button>
            )}
          </div>
        </section>

        <MemoryPanel profile={callerProfile} loading={profileLoading} />

        <TranscriptDock
          open={transcriptOpen}
          onToggle={() => setTranscriptOpen((open) => !open)}
          messages={messages}
          hasConnected={hasConnectedOnce}
        />
      </main>
    </div>
  );
}
