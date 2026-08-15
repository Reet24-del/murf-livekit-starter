const HANDOFF_ANNOUNCEMENT =
  /(?:connect(?:ing)? you to (?:our )?crop problem specialist|crop problem specialist se connect|फसल समस्या विशेषज्ञ से जोड़)/i;

export const SPECIALIST_SIGNAL_TOPIC = 'kisan.sahayak.agent';

/**
 * @param {string} payload
 * @returns {'connecting' | 'active' | null}
 */
export function parseSpecialistSignal(payload) {
  try {
    const signal = JSON.parse(payload);
    if (signal?.type !== 'specialist_handoff') return null;
    return signal.phase === 'connecting' || signal.phase === 'active' ? signal.phase : null;
  } catch {
    return null;
  }
}

/**
 * @param {readonly { message?: string; from?: { isLocal?: boolean } }[]} messages
 * @returns {'idle' | 'connecting' | 'active'}
 */
export function deriveSpecialistPhase(messages, signaledPhase = null) {
  const agentMessages = messages.filter((message) => message.from?.isLocal !== true);
  const handoffIndex = agentMessages.findIndex((message) =>
    HANDOFF_ANNOUNCEMENT.test(message.message ?? '')
  );

  const transcriptPhase =
    handoffIndex === -1
      ? 'idle'
      : handoffIndex < agentMessages.length - 1
        ? 'active'
        : 'connecting';

  if (signaledPhase === 'active' || transcriptPhase === 'active') return 'active';
  if (signaledPhase === 'connecting' || transcriptPhase === 'connecting') return 'connecting';
  return 'idle';
}

const ACTIVE_CONTENT = {
  connecting: {
    label: 'Reconnecting to the crop specialist',
    hindiLabel: 'फसल विशेषज्ञ से दोबारा जुड़ रही हूँ',
    hint: 'Restoring your specialist conversation',
  },
  listening: {
    label: 'Crop specialist is listening',
    hindiLabel: 'फसल विशेषज्ञ आपकी बात सुन रहे हैं',
    hint: 'Describe the crop symptoms naturally',
  },
  thinking: {
    label: 'Crop specialist is checking the symptoms',
    hindiLabel: 'फसल विशेषज्ञ लक्षणों की जाँच कर रहे हैं',
    hint: 'Reviewing the crop problem you described',
  },
  speaking: {
    label: 'Crop specialist is speaking',
    hindiLabel: 'फसल विशेषज्ञ जवाब दे रहे हैं',
    hint: 'You can interrupt naturally at any time',
  },
};

/**
 * @param {'idle' | 'connecting' | 'active'} phase
 * @param {'ready' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'ended'} voiceState
 */
export function getSpecialistVoiceContent(phase, voiceState) {
  if (phase === 'idle' || voiceState === 'ready' || voiceState === 'ended') return null;

  if (phase === 'connecting') {
    return {
      label: 'Connecting you to the specialist',
      hindiLabel: 'आपको फसल विशेषज्ञ से जोड़ा जा रहा है',
      hint: 'Passing your conversation securely so you do not need to repeat it',
    };
  }

  return ACTIVE_CONTENT[voiceState] ?? ACTIVE_CONTENT.listening;
}
