export type VoiceState = 'ready' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'ended';

export const VOICE_STATE_CONTENT: Record<
  VoiceState,
  { label: string; hindiLabel: string; hint: string }
> = {
  ready: {
    label: 'Kisan Sahayak is Ready',
    hindiLabel: 'किसान सहायक तैयार है',
    hint: 'English · हिंदी · Hinglish — automatic',
  },
  connecting: {
    label: 'Connecting to Kisan Sahayak',
    hindiLabel: 'किसान सहायक से जुड़ रही हूँ',
    hint: 'Setting up your secure voice session',
  },
  listening: {
    label: 'I am listening',
    hindiLabel: 'मैं आपकी बात सुन रही हूँ',
    hint: 'Speak naturally in English, Hindi, or Hinglish',
  },
  thinking: {
    label: 'Finding the best answer',
    hindiLabel: 'सही जवाब खोज रही हूँ',
    hint: 'Checking your question and live tools',
  },
  speaking: {
    label: 'Kisan Sahayak is speaking',
    hindiLabel: 'किसान सहायक जवाब दे रही है',
    hint: 'You can interrupt naturally at any time',
  },
  ended: {
    label: 'Call ended',
    hindiLabel: 'कॉल समाप्त हो गई है',
    hint: 'Your saved memory will be available next time',
  },
};
