'use client';

import { useEffect, useRef } from 'react';
import { MicrophoneIcon } from './portal-icons';
import styles from './voice-portal.module.css';
import type { VoiceState } from './voice-state';

interface VoiceOrbProps {
  state: VoiceState;
  userVolume: number;
  agentVolume: number;
}

const RAY_COUNT = 48;
const CENTER = 160;
const INNER_RADIUS = 118;

export function VoiceOrb({ state, userVolume, agentVolume }: VoiceOrbProps) {
  const raysRef = useRef<SVGLineElement[]>([]);
  const volumeRef = useRef({ userVolume, agentVolume });

  useEffect(() => {
    volumeRef.current = { userVolume, agentVolume };
  }, [agentVolume, userVolume]);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    let frame = 0;
    let phase = 0;
    let smoothedVolume = 0;
    const tick = () => {
      phase += 0.04;
      const measuredVolume =
        state === 'speaking' ? volumeRef.current.agentVolume : volumeRef.current.userVolume;
      const idlePulse = state === 'ready' || state === 'ended' ? 0.05 : 0.1;
      smoothedVolume += (measuredVolume + idlePulse - smoothedVolume) * 0.16;

      raysRef.current.forEach((ray, index) => {
        const angle = (index / RAY_COUNT) * Math.PI * 2;
        const wave = Math.sin(phase * 3 + index * 0.56) * 6;
        const length = INNER_RADIUS + 14 + wave + smoothedVolume * 58;
        ray.setAttribute('x2', String(CENTER + Math.cos(angle) * length));
        ray.setAttribute('y2', String(CENTER + Math.sin(angle) * length));
        ray.style.opacity = String(0.24 + Math.min(smoothedVolume * 1.8, 0.65));
      });
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [state]);

  return (
    <div className={styles.orb} data-state={state}>
      <div className={styles.waveLine} aria-hidden="true" />
      <svg aria-hidden="true" viewBox="0 0 320 320" className={styles.rays}>
        {Array.from({ length: RAY_COUNT }, (_, index) => {
          const angle = (index / RAY_COUNT) * Math.PI * 2;
          // Fixed precision keeps server and browser SVG attributes byte-identical.
          const x = (CENTER + Math.cos(angle) * INNER_RADIUS).toFixed(3);
          const y = (CENTER + Math.sin(angle) * INNER_RADIUS).toFixed(3);
          return (
            <line
              key={index}
              ref={(node) => {
                if (node) raysRef.current[index] = node;
              }}
              x1={x}
              y1={y}
              x2={x}
              y2={y}
            />
          );
        })}
      </svg>
      <div className={styles.energySphere} aria-hidden="true">
        <div className={styles.energyMesh} />
        <div className={styles.orbCore}>
          <MicrophoneIcon className={styles.orbMicrophone} />
        </div>
      </div>
    </div>
  );
}
