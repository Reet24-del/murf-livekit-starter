'use client';

import type { AppConfig } from '@/app-config';
import { KisanSahayakView } from './kisan-sahayak-view';

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  return <KisanSahayakView appConfig={appConfig} />;
}
