'use client';

import { useMemo } from 'react';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import type { AppConfig } from '@/app-config';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import { getSandboxTokenSource } from '@/lib/utils';

function AppSetup() {
  useDebugMode({ enabled: false });
  useAgentErrors();

  return null;
}

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  const tokenSource = useMemo(() => {
    if (typeof process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT === 'string') {
      return getSandboxTokenSource(appConfig);
    }
    const loc =
      typeof window !== 'undefined'
        ? localStorage.getItem('detected_location') || 'Lucknow, Uttar Pradesh'
        : 'Lucknow, Uttar Pradesh';
    const encodedLoc = encodeURIComponent(loc);

    let userId = 'unknown';
    if (typeof window !== 'undefined') {
      let storedId = localStorage.getItem('user_id');
      if (!storedId) {
        storedId = `farmer_${Math.floor(100000 + Math.random() * 900000)}`;
        localStorage.setItem('user_id', storedId);
      }
      userId = storedId;
    }

    return TokenSource.endpoint(`/api/token?location=${encodedLoc}&user_id=${userId}`);
  }, [appConfig]);

  const session = useSession(
    tokenSource,
    appConfig.agentName ? { agentName: appConfig.agentName } : undefined
  );

  return (
    <AgentSessionProvider session={session} volume={1.0}>
      <AppSetup />
      <main className="min-h-svh w-full">
        <ViewController appConfig={appConfig} />
      </main>
      <StartAudioButton label="Start Audio" />
      <Toaster
        icons={{
          warning: <WarningIcon weight="bold" />,
        }}
        position="top-center"
        className="toaster group"
        style={
          {
            '--normal-bg': 'var(--popover)',
            '--normal-text': 'var(--popover-foreground)',
            '--normal-border': 'var(--border)',
          } as React.CSSProperties
        }
      />
    </AgentSessionProvider>
  );
}
