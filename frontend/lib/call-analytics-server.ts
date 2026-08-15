import { execFile } from 'node:child_process';
import path from 'node:path';
import { promisify } from 'node:util';
import 'server-only';
import type { AnalyticsFilters, AnalyticsPayload } from './call-analytics';

const execFileAsync = promisify(execFile);
const backendDir = path.join(process.cwd(), '../backend');
const python = process.env.CALL_ANALYTICS_PYTHON ?? path.join(backendDir, '.venv/bin/python');
const script = path.join(backendDir, 'src/call_analytics_cli.py');
const preferred = process.env.CALL_ANALYTICS_DB_PATH ?? path.join(backendDir, 'memory.db');

function resolveDatabasePath(): string {
  return preferred;
}

export async function getCallAnalytics(filters: AnalyticsFilters): Promise<AnalyticsPayload> {
  const args = [
    script,
    'summary',
    '--days',
    String(filters.days),
    '--channel',
    filters.channel,
    '--language',
    filters.language,
    '--outcome',
    filters.outcome,
    '--db-path',
    resolveDatabasePath(),
  ];
  const { stdout } = await execFileAsync(python, args, {
    cwd: backendDir,
    encoding: 'utf8',
    maxBuffer: 1024 * 1024,
  });
  const payload = JSON.parse(stdout) as AnalyticsPayload;
  if (!payload.summary || !Array.isArray(payload.trend) || !Array.isArray(payload.recent_calls)) {
    throw new Error('Invalid call analytics response.');
  }
  return payload;
}
