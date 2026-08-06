'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAgent, useSessionContext, useSessionMessages } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';

interface KisanSahayakViewProps {
  appConfig: AppConfig;
}

export function KisanSahayakView({ appConfig }: KisanSahayakViewProps) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const { state: agentState } = useAgent();
  const [lang, setLang] = useState<'en' | 'hi'>('en');
  const [transcriptOpen, setTranscriptOpen] = useState(false);

  // Animation state refs
  const raysRef = useRef<SVGLineElement[]>([]);
  const animationFrameRef = useRef<number | null>(null);

  // Determine current active state based on LiveKit connection & agent status
  let currentState: 'idle' | 'listening' | 'thinking' | 'speaking' = 'idle';
  if (session.isConnected) {
    if (agentState === 'listening') {
      currentState = 'listening';
    } else if (agentState === 'thinking') {
      currentState = 'thinking';
    } else if (agentState === 'speaking') {
      currentState = 'speaking';
    } else {
      currentState = 'idle';
    }
  }

  // Set up values for states
  const STATES = {
    idle: {
      color: '#4C6656',
      label: session.isConnected ? 'Sahayak is Idle' : 'Tap to talk',
      hi: session.isConnected ? 'सहायक शांत है' : 'बोलने के लिए दबाएं',
      hint: session.isConnected ? 'Connected · Active' : 'Tap to talk · टैप करें',
    },
    listening: {
      color: '#E8A93B',
      label: 'Listening…',
      hi: 'सुन रहा हूँ…',
      hint: 'Listening — speak now',
    },
    thinking: {
      color: '#C97B3D',
      label: 'Thinking…',
      hi: 'सोच रहा हूँ…',
      hint: 'Finding the best advice',
    },
    speaking: {
      color: '#7FB35C',
      label: 'Speaking…',
      hi: 'बोल रहा हूँ…',
      hint: 'Sahayak is answering',
    },
  };

  const activeState = STATES[currentState];

  // Ray visualizer animation loop
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

      // Map currentState to target amplitudes
      if (currentState === 'idle') {
        targetAmplitude = 0.1 + Math.sin(t * 0.6) * 0.02;
      } else if (currentState === 'listening') {
        targetAmplitude = 0.35 + Math.random() * 0.55;
      } else if (currentState === 'thinking') {
        targetAmplitude = 0.28 + Math.sin(t * 2.2) * 0.1;
      } else if (currentState === 'speaking') {
        targetAmplitude = 0.3 + Math.random() * 0.5 * (0.6 + 0.4 * Math.sin(t * 1.7));
      }

      amplitude += (targetAmplitude - amplitude) * 0.18;

      raysRef.current.forEach((line, i) => {
        if (!line) return;
        const angle = (i / RAY_COUNT) * Math.PI * 2;
        const wobble =
          currentState === 'thinking'
            ? Math.sin(t * 3 + i * 0.5) * 0.5 + 0.5
            : (Math.sin(t * 4 + i * 1.3) * 0.5 + 0.5) * amplitude + Math.random() * 0.15;

        const len = R_INNER + 6 + wobble * 26 * (currentState === 'idle' ? 0.3 : 1);
        const x2 = CX + Math.cos(angle) * len;
        const y2 = CY + Math.sin(angle) * len;

        line.setAttribute('x2', x2.toFixed(2));
        line.setAttribute('y2', y2.toFixed(2));
        line.style.stroke = activeState.color;
        line.style.opacity = (0.35 + wobble * 0.65).toFixed(2);
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
  const handleTalkClick = () => {
    if (session.isConnected) {
      session.end?.();
    } else {
      session.start?.();
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
              <b>29°C</b> · Partly cloudy · Lucknow
            </div>
            <div className="weather-advisory">Good day to irrigate</div>
          </div>

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
                    currentState === 'idle' ? 'none' : `0 0 46px 4px ${activeState.color}45`,
                }}
              >
                <svg
                  className="sprout"
                  id="sprout"
                  viewBox="0 0 24 24"
                  fill="none"
                  style={{
                    color: activeState.color,
                    transform:
                      currentState === 'speaking' || currentState === 'listening'
                        ? 'scale(1.08)'
                        : 'scale(1)',
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
                  fontSize: lang === 'hi' ? '14px' : '27px',
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
                  fontSize: lang === 'hi' ? '27px' : '14px',
                  color: lang === 'hi' ? 'var(--ink-primary)' : 'var(--ink-muted)',
                  marginTop: '3px',
                }}
              >
                {activeState.hi}
              </div>
            </div>
          </div>

          {/* transcript */}
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
            &nbsp;Conversation
          </button>

          <div className={`transcript-box ${transcriptOpen ? 'open' : ''}`} id="transcript">
            {messages.length === 0 ? (
              <div className="t-line w-full justify-center text-center text-xs opacity-60">
                <span className="t-text">No conversation yet. Tap button to start talking.</span>
              </div>
            ) : (
              messages.map((m) => {
                const isUser = m.from?.isLocal === true;
                return (
                  <div className="t-line" key={m.id}>
                    <span className={`t-tag ${isUser ? 'farmer' : 'agent'}`}>
                      {isUser ? 'You' : 'Sahayak'}
                    </span>
                    <span className="t-text">{m.message}</span>
                  </div>
                );
              })
            )}
          </div>

          {/* talk control */}
          <div className="control-row">
            <button
              className={`talk-btn is-${currentState}`}
              id="talkBtn"
              onClick={handleTalkClick}
              aria-live="polite"
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

            <div className="lang-toggle">
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
