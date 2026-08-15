import { ChatIcon, ChevronIcon, SproutIcon } from './portal-icons';
import styles from './voice-portal.module.css';

export interface TranscriptMessage {
  id: string;
  message: string;
  from?: { isLocal?: boolean };
}

interface TranscriptDockProps {
  open: boolean;
  onToggle: () => void;
  messages: readonly TranscriptMessage[];
  hasConnected: boolean;
}

export function TranscriptDock({ open, onToggle, messages, hasConnected }: TranscriptDockProps) {
  return (
    <section className={styles.transcriptDock} aria-labelledby="transcript-title">
      <button
        type="button"
        className={styles.transcriptToggle}
        onClick={onToggle}
        aria-expanded={open}
        aria-controls="voice-transcript"
      >
        <span className={styles.transcriptTitle}>
          <ChatIcon aria-hidden="true" />
          <span id="transcript-title">Conversation transcript</span>
        </span>
        <ChevronIcon
          className={open ? styles.chevronOpen : styles.chevronClosed}
          aria-hidden="true"
        />
      </button>
      <div id="voice-transcript" className={styles.transcriptBody} hidden={!open} role="log">
        {messages.length > 0 ? (
          messages.map((item) => {
            const isUser = item.from?.isLocal === true;
            return (
              <div className={styles.transcriptLine} key={item.id}>
                <span
                  className={isUser ? styles.userAvatar : styles.agentAvatar}
                  aria-hidden="true"
                >
                  {isUser ? <span>U</span> : <SproutIcon />}
                </span>
                <strong className={isUser ? styles.userName : styles.agentName}>
                  {isUser ? 'You' : 'Kisan Sahayak'}
                </strong>
                <p>{item.message}</p>
              </div>
            );
          })
        ) : (
          <p className={styles.transcriptEmpty}>
            {hasConnected
              ? 'Connection established. Speak naturally to begin.'
              : 'Your live conversation will appear here.'}
          </p>
        )}
      </div>
    </section>
  );
}
