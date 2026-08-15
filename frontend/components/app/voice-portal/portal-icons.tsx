import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

export function SproutIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 21V10" />
      <path d="M12 13C8 13 5 10 5 6c4 0 7 2 7 6" />
      <path d="M12 15c0-4 3-7 7-8 0 4-2 7-7 8" />
    </svg>
  );
}

export function MicrophoneIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <rect x="9" y="3" width="6" height="12" rx="3" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M9 21h6" />
    </svg>
  );
}

export function PhoneIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M7 3H4.5A1.5 1.5 0 0 0 3 4.5C3 13.6 10.4 21 19.5 21a1.5 1.5 0 0 0 1.5-1.5V17l-4.2-1.1-1.1 2.2a15 15 0 0 1-9.8-9.8l2.2-1.1L7 3Z" />
      <path d="M15 5c2 0 4 2 4 4M15 2c4 0 7 3 7 7" />
    </svg>
  );
}

export function CloudRainIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M6 17h11a4 4 0 0 0 .5-8A6 6 0 0 0 6 8.2 4.5 4.5 0 0 0 6 17Z" />
      <path d="m8 20-1 2m5-2-1 2m5-2-1 2" />
    </svg>
  );
}

export function BrainIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M9.5 4.5A3 3 0 0 0 4 6a3 3 0 0 0-1 5.2A3.5 3.5 0 0 0 6 17a3 3 0 0 0 3.5 2.5V4.5Zm5 0A3 3 0 0 1 20 6a3 3 0 0 1 1 5.2A3.5 3.5 0 0 1 18 17a3 3 0 0 1-3.5 2.5V4.5ZM6 9h3.5m-4 5h4m8.5-5h-3.5m4 5h-4" />
    </svg>
  );
}

export function NoteIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M6 3h9l4 4v14H6V3Z" />
      <path d="M15 3v5h4M9 12h7M9 16h7" />
    </svg>
  );
}

export function ChatIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 4h16v12H9l-5 4V4Z" />
      <path d="M8 9h8m-8 3h5" />
    </svg>
  );
}

export function ResetIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M20 6v5h-5" />
      <path d="M18.5 16a8 8 0 1 1 .8-9.2L20 11" />
    </svg>
  );
}

export function ChevronIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="m6 14 6-6 6 6" />
    </svg>
  );
}
