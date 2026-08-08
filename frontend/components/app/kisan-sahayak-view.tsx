'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ConnectionState } from 'livekit-client';
import {
  useSessionContext,
  useSessionMessages,
  useTrackVolume,
  useVoiceAssistant,
} from '@livekit/components-react';
import type { AppConfig } from '@/app-config';

interface KisanSahayakViewProps {
  appConfig: AppConfig;
}

export function KisanSahayakView({ appConfig }: KisanSahayakViewProps) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const { state: agentState, audioTrack } = useVoiceAssistant();
  const [lang, setLang] = useState<'en' | 'hi'>('en');
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  const [hasConnectedOnce, setHasConnectedOnce] = useState(false);
  const [micError, setMicError] = useState<'permission_denied' | 'other' | null>(null);
  const [micPermissionStatus, setMicPermissionStatus] = useState<PermissionState | 'unknown'>(
    'unknown'
  );

  const [detectedLocation, setDetectedLocation] = useState<string>('Lucknow, Uttar Pradesh');
  const [weatherText, setWeatherText] = useState<string>('Partly cloudy');
  const [temp, setTemp] = useState<string>('29°C');
  const [advisory, setAdvisory] = useState<string>('Good day to irrigate');

  // Animation state refs
  const raysRef = useRef<SVGLineElement[]>([]);
  const animationFrameRef = useRef<number | null>(null);

  // Track if we have connected once
  useEffect(() => {
    if (session.isConnected) {
      setHasConnectedOnce(true);
      setTranscriptOpen(true); // Open transcript by default when connected
    }
  }, [session.isConnected]);

  // Monitor microphone permission settings
  useEffect(() => {
    if (typeof navigator !== 'undefined' && navigator.permissions && navigator.permissions.query) {
      navigator.permissions
        .query({ name: 'microphone' as PermissionName })
        .then((permissionStatus) => {
          setMicPermissionStatus(permissionStatus.state);
          permissionStatus.onchange = () => {
            setMicPermissionStatus(permissionStatus.state);
            if (permissionStatus.state === 'granted') {
              setMicError(null);
            }
          };
        })
        .catch((e) => console.log('Query permission error', e));
    }
  }, []);

  // Fetch Geolocation and Local Weather on load
  useEffect(() => {
    if (typeof window === 'undefined') return;

    fetch('https://ipapi.co/json/')
      .then((res) => res.json())
      .then((geo) => {
        if (geo.city && geo.region) {
          const loc = `${geo.city}, ${geo.region}`;
          setDetectedLocation(loc);
          localStorage.setItem('detected_location', loc);

          if (geo.latitude && geo.longitude) {
            fetch(
              `https://api.open-meteo.com/v1/forecast?latitude=${geo.latitude}&longitude=${geo.longitude}&current_weather=true`
            )
              .then((r) => r.json())
              .then((w) => {
                if (w.current_weather) {
                  setTemp(`${Math.round(w.current_weather.temperature)}°C`);
                  const codes: Record<number, string> = {
                    0: 'Clear sky',
                    1: 'Mainly clear',
                    2: 'Partly cloudy',
                    3: 'Overcast',
                    45: 'Foggy',
                    48: 'Foggy',
                    51: 'Drizzle',
                    53: 'Drizzle',
                    55: 'Drizzle',
                    61: 'Light rain',
                    63: 'Rain',
                    65: 'Heavy rain',
                    71: 'Snow',
                    73: 'Snow',
                    75: 'Heavy snow',
                    80: 'Rain showers',
                    81: 'Rain showers',
                    82: 'Heavy showers',
                    95: 'Thunderstorm',
                  };
                  const desc = codes[w.current_weather.weathercode as number] || 'Clear sky';
                  setWeatherText(desc);

                  const tempVal = w.current_weather.temperature;
                  if (w.current_weather.weathercode >= 60) {
                    setAdvisory('Postpone irrigation');
                  } else if (tempVal > 32) {
                    setAdvisory('Water crops early');
                  } else {
                    setAdvisory('Good day to irrigate');
                  }
                }
              })
              .catch((err) => console.log('Weather lookup error:', err));
          }
        }
      })
      .catch((err) => console.log('Location fetch error:', err));
  }, []);

  // Track volumes
  const agentVolume = useTrackVolume(audioTrack, {
    fftSize: 256,
    smoothingTimeConstant: 0.4,
  });

  const userVolume = useTrackVolume(session.local?.microphoneTrack, {
    fftSize: 256,
    smoothingTimeConstant: 0.4,
  });

  const volumesRef = useRef({ user: 0, agent: 0 });
  useEffect(() => {
    volumesRef.current = { user: userVolume, agent: agentVolume };
  }, [userVolume, agentVolume]);

  // Determine current active state mapped to the required 5 States (plus sub-state thinking)
  let currentState: 'ready' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'ended' =
    'ready';

  if (
    session.connectionState === ConnectionState.Connecting ||
    session.connectionState === ConnectionState.Reconnecting
  ) {
    currentState = 'connecting';
  } else if (session.isConnected) {
    if (agentState === 'listening') {
      currentState = 'listening';
    } else if (agentState === 'speaking') {
      currentState = 'speaking';
    } else if (agentState === 'thinking') {
      currentState = 'thinking';
    } else {
      currentState = 'listening'; // default active connected state
    }
  } else {
    currentState = hasConnectedOnce ? 'ended' : 'ready';
  }

  // Set up values for states
  const STATES = {
    ready: {
      color: '#7FB35C',
      label: 'Kisan Sahayak is Ready',
      hi: 'किसान सहायक तैयार है',
      hint: 'Tap the green button below to start your consultation · बातचीत शुरू करने के लिए नीचे दबाएं',
    },
    connecting: {
      color: '#C97B3D',
      label: 'Connecting…',
      hi: 'किसान सहायक से जुड़ रहे हैं…',
      hint: 'Please wait while we connect to Kisan Sahayak · कृपया प्रतीक्षा करें',
    },
    listening: {
      color: '#E8A93B',
      label: 'Listening to you…',
      hi: 'आपकी बात सुन रहे हैं…',
      hint: 'Speak naturally · किसान सहायक आपकी बात सुन रही हैं',
    },
    thinking: {
      color: '#C97B3D',
      label: 'Thinking…',
      hi: 'सोच रही हूँ…',
      hint: 'Finding the best agricultural advice · कृपया प्रतीक्षा करें',
    },
    speaking: {
      color: '#7FB35C',
      label: 'Sahayak is Speaking…',
      hi: 'किसान सहायक बोल रही हैं…',
      hint: 'Do not click · किसान सहायक जवाब दे रही हैं',
    },
    ended: {
      color: '#6F8577',
      label: 'Call Ended',
      hi: 'कॉल समाप्त हो गई है',
      hint: 'Conversation finished · Click below to start again · फिर से बात करने के लिए नीचे दबाएं',
    },
  };

  const activeState = STATES[currentState];

  // Ray visualizer animation loop driven by real-time track volumes
  useEffect(() => {
    const RAY_COUNT = 28;
    const CX = 125;
    const CY = 125;
    const R_INNER = 78;

    let t = 0;
    let amplitude = 0.08;
    let targetAmplitude = 0.08;

    const tick = () => {
      t += 0.045;

      const { user: uVol, agent: aVol } = volumesRef.current;

      // Map currentState to target amplitudes
      if (currentState === 'ready' || currentState === 'ended') {
        targetAmplitude = 0.08 + Math.sin(t * 0.6) * 0.015;
      } else if (currentState === 'connecting') {
        targetAmplitude = 0.14 + Math.sin(t * 2.2) * 0.05;
      } else if (currentState === 'listening') {
        // userVolume drives rays
        targetAmplitude = 0.12 + uVol * 1.6;
      } else if (currentState === 'thinking') {
        targetAmplitude = 0.18 + Math.sin(t * 3.0) * 0.06;
      } else if (currentState === 'speaking') {
        // agentVolume drives rays
        targetAmplitude = 0.12 + aVol * 1.8;
      }

      amplitude += (targetAmplitude - amplitude) * 0.22;

      raysRef.current.forEach((line, i) => {
        if (!line) return;
        const angle = (i / RAY_COUNT) * Math.PI * 2;

        let wobble = 0;
        if (currentState === 'ready' || currentState === 'ended') {
          wobble = (Math.sin(t * 2 + i * 0.5) * 0.5 + 0.5) * amplitude;
        } else if (currentState === 'connecting' || currentState === 'thinking') {
          wobble = (Math.sin(t * 3.5 + i * 0.8) * 0.5 + 0.5) * amplitude;
        } else if (currentState === 'listening') {
          wobble = (Math.sin(t * 4.5 + i * 1.1) * 0.5 + 0.5) * amplitude + uVol * 0.4;
        } else if (currentState === 'speaking') {
          wobble = (Math.sin(t * 5 + i * 1.3) * 0.5 + 0.5) * amplitude + aVol * 0.5;
        }

        const len =
          R_INNER +
          6 +
          wobble * 28 * (currentState === 'ready' || currentState === 'ended' ? 0.35 : 1.15);
        const x2 = CX + Math.cos(angle) * len;
        const y2 = CY + Math.sin(angle) * len;

        line.setAttribute('x2', x2.toFixed(2));
        line.setAttribute('y2', y2.toFixed(2));
        line.style.stroke = activeState.color;
        line.style.opacity = (0.28 + wobble * 0.72).toFixed(2);
      });

      animationFrameRef.current = requestAnimationFrame(tick);
    };

    tick();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [currentState, activeState.color]);

  // Handle talk button click
  const handleTalkClick = async () => {
    if (session.connectionState === ConnectionState.Disconnected) {
      try {
        setMicError(null);
        await session.start?.();
      } catch (err: unknown) {
        const error = err as Error;
        console.error('Failed to start session:', error);
        if (
          error?.name === 'NotAllowedError' ||
          error?.message?.toLowerCase().includes('permission') ||
          error?.message?.toLowerCase().includes('allowed') ||
          error?.message?.toLowerCase().includes('denied')
        ) {
          setMicError('permission_denied');
        } else {
          setMicError('other');
        }
      }
    }
  };

  const handleStartAgain = async () => {
    setHasConnectedOnce(false);
    setMicError(null);
    try {
      await session.start?.();
    } catch (err: unknown) {
      const error = err as Error;
      console.error('Failed to restart session:', error);
      if (
        error?.name === 'NotAllowedError' ||
        error?.message?.toLowerCase().includes('permission') ||
        error?.message?.toLowerCase().includes('allowed') ||
        error?.message?.toLowerCase().includes('denied')
      ) {
        setMicError('permission_denied');
      } else {
        setMicError('other');
      }
    }
  };

  // Render SVG Rays initial lines
  const RAY_COUNT = 28;
  const CX = 125;
  const CY = 125;
  const R_INNER = 78;
  const rays = Array.from({ length: RAY_COUNT }).map((_, i) => {
    const angle = (i / RAY_COUNT) * Math.PI * 2;
    const x1 = CX + Math.cos(angle) * R_INNER;
    const y1 = CY + Math.sin(angle) * R_INNER;
    return (
      <line
        key={i}
        ref={(el) => {
          if (el) raysRef.current[i] = el;
        }}
        className="ray"
        x1={x1.toFixed(2)}
        y1={y1.toFixed(2)}
        x2={x1.toFixed(2)}
        y2={y1.toFixed(2)}
      />
    );
  });

  return (
    <>
      {/* Isolated styling from custom template */}
      <style
        dangerouslySetInnerHTML={{
          __html: `
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
          --surface-base: #0F241A;
          --surface-raised: #17301F;
          --surface-raised-2: #1D3A26;
          --ink-primary: #F6F2E7;
          --ink-muted: #A9BFAE;
          --ink-faint: #6F8577;
          --accent-listening: #E8A93B;
          --accent-thinking:  #C97B3D;
          --accent-responding:#7FB35C;
          --accent-idle:      #4C6656;
          --danger: #E4694A;
          --radius-lg: 22px;
          --radius-md: 14px;
          --radius-sm: 8px;
          --font-display: 'Fraunces', serif;
          --font-body: 'Inter', sans-serif;
          --font-devanagari: 'Noto Sans Devanagari', sans-serif;
          --font-mono: 'JetBrains Mono', monospace;
        }

        .kisan-body {
          background: var(--surface-base) !important;
          color: var(--ink-primary) !important;
          font-family: var(--font-body);
        }

        .field-glow {
          position: fixed; inset: 0; z-index: 0; pointer-events: none;
          background:
            radial-gradient(ellipse 60% 40% at 50% 8%, rgba(232,169,59,0.10), transparent 60%),
            radial-gradient(ellipse 80% 50% at 20% 100%, rgba(127,179,92,0.10), transparent 60%),
            radial-gradient(ellipse 80% 50% at 85% 95%, rgba(201,123,61,0.08), transparent 60%);
        }

        .furrows {
          position: fixed; left: 0; right: 0; bottom: 0; height: 38vh; z-index: 0; pointer-events: none;
          opacity: 0.35;
          background-image: repeating-linear-gradient(
            100deg,
            rgba(127,179,92,0.05) 0px,
            rgba(127,179,92,0.05) 2px,
            transparent 2px,
            transparent 34px
          );
          -webkit-mask-image: linear-gradient(to top, black, transparent);
          mask-image: linear-gradient(to top, black, transparent);
          animation: driftFurrows 26s linear infinite;
        }

        @keyframes driftFurrows {
          from { background-position-x: 0; }
          to { background-position-x: 340px; }
        }

        .app-container {
          position: relative; z-index: 1;
          max-width: 460px;
          margin: 0 auto;
          min-height: 100vh;
          display: flex; flex-direction: column;
          padding: 18px 18px 24px;
        }

        .statusbar {
          display: flex; align-items: center; justify-content: space-between;
          padding: 6px 2px 18px;
        }

        .brand {
          display: flex; align-items: center; gap: 9px;
        }

        .brand-mark {
          width: 26px; height: 26px; flex: none;
        }

        .brand-name {
          font-family: var(--font-mono);
          font-size: 12.5px;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--ink-muted);
        }

        .brand-name b { color: var(--ink-primary); font-weight: 600; }

        .conn {
          display: flex; align-items: center; gap: 6px;
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          color: var(--ink-muted);
        }

        .conn-dot {
          width: 7px; height: 7px; border-radius: 50%;
          background: var(--accent-responding);
          box-shadow: 0 0 0 0 rgba(127,179,92,0.6);
          animation: dotPulse 2.4s ease-out infinite;
        }

        .conn-dot.disconnected {
          background: var(--danger);
          animation: none;
        }

        @keyframes dotPulse {
          0% { box-shadow: 0 0 0 0 rgba(127,179,92,0.45); }
          70% { box-shadow: 0 0 0 7px rgba(127,179,92,0); }
          100% { box-shadow: 0 0 0 0 rgba(127,179,92,0); }
        }

        .weather-chip {
          display: flex; align-items: center; gap: 10px;
          background: var(--surface-raised);
          border: 1px solid rgba(246,242,231,0.06);
          border-radius: var(--radius-md);
          padding: 10px 14px;
          margin-bottom: 18px;
        }

        .weather-icon { width: 30px; height: 30px; flex: none; }
        .weather-text { font-size: 12.5px; color: var(--ink-muted); line-height: 1.4; }
        .weather-text b { color: var(--ink-primary); font-weight: 600; }

        .weather-advisory {
          margin-left: auto;
          font-family: var(--font-mono);
          font-size: 9.5px;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          color: var(--accent-responding);
          background: rgba(127,179,92,0.12);
          padding: 4px 8px;
          border-radius: 999px;
          white-space: nowrap;
        }

        .stage {
          flex: 1;
          display: flex; flex-direction: column; align-items: center; justify-content: center;
          padding: 18px 0 28px;
          min-height: 320px;
        }

        .orb-wrap {
          position: relative;
          width: 250px; height: 250px;
          display: flex; align-items: center; justify-content: center;
        }

        svg.orb-rays {
          position: absolute; inset: 0;
          width: 100%; height: 100%;
          transform: rotate(-90deg);
        }

        .ray {
          stroke: var(--accent-idle);
          stroke-width: 3.2;
          stroke-linecap: round;
          transition: stroke 0.5s ease;
        }

        .orb-core {
          position: relative;
          width: 128px; height: 128px;
          border-radius: 50%;
          background: radial-gradient(circle at 35% 30%, var(--surface-raised-2), var(--surface-base) 72%);
          border: 1px solid rgba(246,242,231,0.08);
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 0 0 0 rgba(232,169,59,0);
          transition: box-shadow 0.6s ease, transform 0.4s ease;
        }

        .sprout {
          width: 52px; height: 52px;
          color: var(--accent-idle);
          transition: color 0.5s ease, transform 0.5s ease;
        }

        .state-label-wrap {
          margin-top: 26px;
          text-align: center;
        }

        .state-label {
          font-family: var(--font-display);
          font-weight: 600;
          font-size: 27px;
          letter-spacing: 0.01em;
          color: var(--ink-primary);
          transition: color 0.4s ease;
        }

        .state-label-hi {
          font-family: var(--font-devanagari);
          font-size: 14px;
          color: var(--ink-muted);
          margin-top: 3px;
        }

        .transcript-toggle {
          display: flex; align-items: center; justify-content: center; gap: 6px;
          background: none; border: none; cursor: pointer;
          font-family: var(--font-mono);
          font-size: 10.5px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--ink-faint);
          padding: 8px;
          margin-bottom: 4px;
          width: 100%;
        }

        .transcript-toggle:hover { color: var(--ink-muted); }
        .chev { width: 9px; height: 9px; transition: transform 0.3s ease; }
        .chev.open { transform: rotate(180deg); }

        .transcript-box {
          background: var(--surface-raised);
          border: 1px solid rgba(246,242,231,0.06);
          border-radius: var(--radius-md);
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.45s ease, padding 0.45s ease, margin 0.45s ease;
          margin-bottom: 0;
          width: 100%;
        }

        .transcript-box.open {
          max-height: 220px;
          padding: 14px 16px;
          margin-bottom: 16px;
          overflow-y: auto;
        }

        .t-line {
          display: flex; gap: 10px;
          font-size: 13px;
          line-height: 1.5;
          margin-bottom: 12px;
          text-align: left;
        }

        .t-line:last-child { margin-bottom: 0; }

        .t-tag {
          font-family: var(--font-mono);
          font-size: 9px;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          padding: 2px 6px;
          border-radius: 5px;
          height: fit-content;
          flex: none;
          margin-top: 2px;
        }

        .t-tag.farmer { background: rgba(232,169,59,0.15); color: var(--accent-listening); }
        .t-tag.agent { background: rgba(127,179,92,0.15); color: var(--accent-responding); }
        .t-text { color: var(--ink-muted); }
        .t-text b { color: var(--ink-primary); font-weight: 500; }

        .control-row {
          display: flex; flex-direction: column; align-items: center; gap: 12px;
          margin-top: 6px;
        }

        .talk-btn {
          position: relative;
          width: 74px; height: 74px;
          border-radius: 50%;
          border: none;
          cursor: pointer;
          background: var(--accent-listening);
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 8px 24px -6px rgba(232,169,59,0.45);
          transition: background 0.4s ease, box-shadow 0.4s ease, transform 0.15s ease;
        }

        .talk-btn:active { transform: scale(0.94); }
        .talk-btn.is-listening { background: var(--accent-listening); box-shadow: 0 8px 26px -6px rgba(232,169,59,0.55); }
        .talk-btn.is-thinking { background: var(--accent-thinking); box-shadow: 0 8px 26px -6px rgba(201,123,61,0.5); }
        .talk-btn.is-speaking { background: var(--accent-responding); box-shadow: 0 8px 26px -6px rgba(127,179,92,0.5); }
        .talk-btn.is-idle { background: var(--surface-raised-2); box-shadow: none; border: 1px solid rgba(246,242,231,0.12); }

        .talk-btn svg { width: 28px; height: 28px; color: #12200F; }
        .talk-btn.is-idle svg { color: var(--ink-primary); }

        .talk-ring {
          position: absolute; inset: -9px;
          border-radius: 50%;
          border: 1.5px solid var(--accent-listening);
          opacity: 0;
        }

        .talk-btn.is-listening .talk-ring { animation: ringPulse 1.5s ease-out infinite; border-color: var(--accent-listening); }
        .talk-btn.is-speaking .talk-ring { animation: ringPulse 1.5s ease-out infinite; border-color: var(--accent-responding); }

        @keyframes ringPulse {
          0% { transform: scale(0.9); opacity: 0.7; }
          100% { transform: scale(1.35); opacity: 0; }
        }

        .talk-hint {
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.05em;
          color: var(--ink-faint);
          text-transform: uppercase;
        }

        .lang-toggle {
          display: flex; align-items: center; justify-content: center; gap: 4px;
          margin-top: 22px;
        }

        .lang-btn {
          font-family: var(--font-mono);
          font-size: 10.5px;
          letter-spacing: 0.05em;
          color: var(--ink-faint);
          background: none; border: none; cursor: pointer;
          padding: 5px 10px;
          border-radius: 999px;
        }

        .lang-btn.active { color: var(--ink-primary); background: var(--surface-raised); }

        @media (max-width: 380px) {
          .orb-wrap { width: 210px; height: 210px; }
          .orb-core { width: 108px; height: 108px; }
          .state-label { font-size: 23px; }
        }

        .mic-error-card {
          background: rgba(228, 105, 74, 0.08);
          border: 1px solid rgba(228, 105, 74, 0.3);
          border-radius: var(--radius-lg);
          padding: 20px;
          margin-top: 18px;
          margin-bottom: 18px;
          text-align: left;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
          backdrop-filter: blur(10px);
          width: 100%;
        }

        .mic-error-title {
          font-family: var(--font-display);
          font-size: 19px;
          font-weight: 600;
          color: var(--danger);
          margin-bottom: 8px;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .mic-error-body {
          font-size: 13px;
          color: var(--ink-primary);
          line-height: 1.5;
        }

        .mic-error-steps {
          margin-top: 10px;
          padding-left: 18px;
          list-style-type: decimal;
          color: var(--ink-muted);
        }

        .mic-error-steps li {
          margin-bottom: 6px;
        }

        .mic-error-retry-btn {
          margin-top: 14px;
          background: var(--danger);
          color: white;
          border: none;
          border-radius: var(--radius-sm);
          padding: 8px 16px;
          font-size: 12px;
          font-family: var(--font-mono);
          cursor: pointer;
          font-weight: 600;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          transition: opacity 0.2s ease;
        }

        .mic-error-retry-btn:hover {
          opacity: 0.9;
        }

        .big-start-btn {
          background: var(--accent-responding);
          color: #12200F;
          font-family: var(--font-display);
          font-weight: 600;
          font-size: 18px;
          padding: 16px 36px;
          border: none;
          border-radius: var(--radius-lg);
          cursor: pointer;
          box-shadow: 0 8px 24px -4px rgba(127,179,92,0.45);
          transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .big-start-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 30px -4px rgba(127,179,92,0.55);
        }

        .big-start-btn:active {
          transform: translateY(1px);
        }

        .pulse-loader {
          position: absolute;
          inset: -12px;
          border-radius: 50%;
          border: 2.5px solid var(--accent-thinking);
          animation: pulseLoaderAnim 1.6s cubic-bezier(0.24, 0, 0.38, 1) infinite;
        }

        @keyframes pulseLoaderAnim {
          0% { transform: scale(0.95); opacity: 0.8; }
          100% { transform: scale(1.4); opacity: 0; }
        }

        .speaking-badge {
          background: rgba(127, 179, 92, 0.15);
          color: var(--accent-responding);
          border: 1px solid rgba(127, 179, 92, 0.25);
          font-family: var(--font-mono);
          font-size: 10.5px;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          padding: 4px 10px;
          border-radius: 999px;
          margin-top: 14px;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }

        .speaking-indicator-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--accent-responding);
          animation: blinkDot 1s alternate infinite;
        }

        @keyframes blinkDot {
          0% { opacity: 0.25; }
          100% { opacity: 1; }
        }
      `,
        }}
      />

      <div className="kisan-body h-full min-h-screen w-full overflow-y-auto">
        <div className="field-glow"></div>
        <div className="furrows"></div>

        <div className="app-container">
          {/* status bar */}
          <div className="statusbar">
            <div className="brand">
              <svg className="brand-mark" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 21c0-5 3-8 3-8s-6-1-6-7c0 0 6-1 6 5 0 0 3-3 3-8"
                  stroke="#E8A93B"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path d="M12 21V11" stroke="#7FB35C" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              <div className="brand-name">
                <b>Kisan</b> Sahayak
              </div>
            </div>
            <div className="conn">
              <span className={`conn-dot ${!session.isConnected ? 'disconnected' : ''}`}></span>
              {session.isConnected ? 'Connected' : 'Disconnected'}
            </div>
          </div>

          {/* weather advisory chip */}
          <div className="weather-chip">
            <svg className="weather-icon" viewBox="0 0 24 24" fill="none">
              <circle cx="9" cy="10" r="5" fill="#E8A93B" opacity="0.9" />
              <path
                d="M13 15.5a4.5 4.5 0 1 1 1.2-8.84A5.5 5.5 0 0 1 19 14.5H8.5"
                stroke="#A9BFAE"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
            </svg>
            <div className="weather-text">
              <b>{temp}</b> · {weatherText} · {detectedLocation.split(',')[0]}
            </div>
            <div className="weather-advisory">{advisory}</div>
          </div>

          {/* Microphone Permission Error Card (Step 4: Handle mic permission errors) */}
          {(micError === 'permission_denied' || micPermissionStatus === 'denied') && (
            <div className="mic-error-card" id="micErrorCard">
              <div className="mic-error-title">
                <svg
                  className="h-5 w-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <span>Microphone Access Blocked</span>
              </div>
              <div className="mic-error-body">
                <p>Kisan Sahayak needs microphone access to listen to your agricultural queries.</p>
                <ol className="mic-error-steps">
                  <li>
                    Click the **Lock icon** 🔒 (or settings icon) next to the website address in the
                    top bar.
                  </li>
                  <li>Locate **Microphone** in the list.</li>
                  <li>Toggle the permission setting to **Allow**.</li>
                  <li>Refresh this page and try starting the call again.</li>
                </ol>
                <button
                  className="mic-error-retry-btn"
                  onClick={() => {
                    setMicError(null);
                    handleTalkClick();
                  }}
                >
                  Try Again
                </button>
              </div>
            </div>
          )}

          {/* reactive orb stage */}
          <div className="stage">
            <div className="orb-wrap">
              <svg className="orb-rays" viewBox="0 0 250 250" id="rays">
                {rays}
              </svg>
              <div
                className="orb-core"
                id="orbCore"
                style={{
                  boxShadow:
                    currentState === 'ready' || currentState === 'ended'
                      ? 'none'
                      : `0 0 46px 6px ${activeState.color}45`,
                  transform:
                    currentState === 'speaking' || currentState === 'listening'
                      ? 'scale(1.08)'
                      : 'scale(1)',
                }}
              >
                {currentState === 'connecting' && <span className="pulse-loader"></span>}
                <svg
                  className="sprout"
                  id="sprout"
                  viewBox="0 0 24 24"
                  fill="none"
                  style={{
                    color: activeState.color,
                  }}
                >
                  <path
                    d="M12 21c0-6 3.5-9.5 3.5-9.5s-7-1-7-8c0 0 7-1.2 7 6 0 0 3.5-3.5 3.5-9.5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M12 21V9"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
            </div>

            <div className="state-label-wrap">
              <div
                className="state-label"
                id="stateLabel"
                style={{
                  fontFamily: lang === 'hi' ? 'var(--font-devanagari)' : 'var(--font-display)',
                  fontSize: lang === 'hi' ? '18px' : '27px',
                  color: lang === 'hi' ? 'var(--ink-muted)' : 'var(--ink-primary)',
                }}
              >
                {activeState.label}
              </div>
              <div
                className="state-label-hi"
                id="stateLabelHi"
                style={{
                  fontFamily: lang === 'hi' ? 'var(--font-display)' : 'var(--font-devanagari)',
                  fontSize: lang === 'hi' ? '27px' : '16px',
                  color: lang === 'hi' ? 'var(--ink-primary)' : 'var(--ink-muted)',
                  marginTop: '4px',
                }}
              >
                {activeState.hi}
              </div>

              {/* Clear speaker badge (Step 3: Make it clear who is speaking) */}
              {session.isConnected && (
                <div
                  className="speaking-badge"
                  style={{ borderColor: activeState.color + '40', color: activeState.color }}
                >
                  {currentState === 'speaking' && (
                    <span
                      className="speaking-indicator-dot"
                      style={{ backgroundColor: activeState.color }}
                    ></span>
                  )}
                  {currentState === 'speaking' ? 'Sahayak is speaking · सहायक बोल रही हैं' : ''}
                  {currentState === 'listening' ? 'Listening to you · आपकी बात सुन रहे हैं' : ''}
                  {currentState === 'thinking' ? 'Thinking · विचार कर रहे हैं' : ''}
                </div>
              )}
            </div>
          </div>

          {/* transcript - hidden in ready state, shown/collapsible in conversation, visible in call ended */}
          {currentState !== 'ready' && (
            <>
              <button
                className="transcript-toggle"
                id="transcriptToggle"
                onClick={() => setTranscriptOpen(!transcriptOpen)}
              >
                <svg
                  className={`chev ${transcriptOpen ? 'open' : ''}`}
                  id="chev"
                  viewBox="0 0 12 12"
                  fill="none"
                >
                  <path
                    d="M2 4l4 4 4-4"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                &nbsp;Conversation History / बातचीत का इतिहास
              </button>

              <div className={`transcript-box ${transcriptOpen ? 'open' : ''}`} id="transcript">
                {messages.length === 0 ? (
                  <div className="t-line w-full justify-center text-center text-xs opacity-60">
                    <span className="t-text">Connection established. Start speaking!</span>
                  </div>
                ) : (
                  messages.map((m) => {
                    const isUser = m.from?.isLocal === true;
                    return (
                      <div className="t-line" key={m.id}>
                        <span className={`t-tag ${isUser ? 'farmer' : 'agent'}`}>
                          {isUser ? 'Farmer / किसान' : 'Sahayak / सहायक'}
                        </span>
                        <span className="t-text">{m.message}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </>
          )}

          {/* talk control / actions (Step 2 state-specific controls) */}
          <div className="control-row">
            {currentState === 'ready' && (
              <button className="big-start-btn" id="startCallBtn" onClick={handleTalkClick}>
                <svg
                  className="h-6 w-6 animate-pulse"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 5a2 2 0 012-2h3.28a1 1 0 01.94.725l.548 2.2a1 1 0 01-.321.988l-1.305.98a10.582 10.582 0 004.872 4.872l.98-1.305a1 1 0 01.988-.321l2.2.548a1 1 0 01.725.94V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                  />
                </svg>
                <span>Start Call / बातचीत शुरू करें</span>
              </button>
            )}

            {currentState === 'ended' && (
              <button
                className="big-start-btn"
                id="startAgainBtn"
                onClick={handleStartAgain}
                style={{
                  background: 'var(--surface-raised-2)',
                  color: 'var(--ink-primary)',
                  border: '1px solid rgba(246,242,231,0.15)',
                }}
              >
                <svg
                  className="h-6 w-6"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3m-3-3v12"
                  />
                </svg>
                <span>Start Again / फिर से शुरू करें</span>
              </button>
            )}

            {(currentState === 'connecting' ||
              currentState === 'listening' ||
              currentState === 'speaking' ||
              currentState === 'thinking') && (
              <>
                <button
                  className={`talk-btn is-${currentState}`}
                  id="talkBtn"
                  onClick={() => {
                    // Hands-free active
                  }}
                  aria-live="polite"
                  style={{ cursor: 'default' }}
                >
                  <span className="talk-ring"></span>
                  <svg id="btnIcon" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M19 11a7 7 0 0 1-14 0"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M12 18v3"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                <div className="talk-hint" id="talkHint">
                  {activeState.hint}
                </div>
              </>
            )}

            {session.isConnected && (
              <button
                className="end-call-btn"
                onClick={() => session.end?.()}
                style={{
                  marginTop: '12px',
                  background: 'rgba(239, 68, 68, 0.18)',
                  color: '#f87171',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '999px',
                  padding: '8px 20px',
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)',
                  letterSpacing: '0.06em',
                  cursor: 'pointer',
                  fontWeight: 600,
                  transition: 'all 0.2s ease',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.28)';
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.18)';
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                }}
              >
                END CALL / कॉल समाप्त करें
              </button>
            )}

            <div className="lang-toggle" style={{ marginTop: '16px' }}>
              <button
                className={`lang-btn ${lang === 'en' ? 'active' : ''}`}
                onClick={() => setLang('en')}
              >
                EN
              </button>
              <button
                className={`lang-btn ${lang === 'hi' ? 'active' : ''}`}
                onClick={() => setLang('hi')}
              >
                हिं
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
