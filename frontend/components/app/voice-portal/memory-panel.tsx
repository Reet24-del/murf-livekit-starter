import type { CallerProfileSummary } from '@/lib/caller-profile';
import { BrainIcon, NoteIcon } from './portal-icons';
import styles from './voice-portal.module.css';

interface MemoryPanelProps {
  profile: CallerProfileSummary | null;
  loading: boolean;
}

function known(value: string | null | undefined): string | null {
  return value && value !== 'Unknown' ? value : null;
}

export function MemoryPanel({ profile, loading }: MemoryPanelProps) {
  const crops = known(profile?.crops_grown);
  const district = known(profile?.district);
  const summary = known(profile?.conversation_memory);

  return (
    <section className={`${styles.panel} ${styles.memoryPanel}`} aria-labelledby="memory-title">
      <div className={styles.panelHeading}>
        <BrainIcon aria-hidden="true" />
        <h2 id="memory-title">Saved memory</h2>
      </div>
      {loading ? (
        <p className={styles.panelMuted} aria-busy="true">
          Loading saved profile…
        </p>
      ) : profile ? (
        <>
          <p className={styles.memoryFacts}>
            {crops || 'No crops saved'} · {district || 'No district saved'}
          </p>
          <div className={styles.panelDivider} />
          <p className={styles.memorySummary}>
            <NoteIcon aria-hidden="true" />
            <span>{summary || 'No conversation summary saved yet.'}</span>
          </p>
        </>
      ) : (
        <p className={styles.panelMuted}>No saved profile found yet.</p>
      )}
    </section>
  );
}
