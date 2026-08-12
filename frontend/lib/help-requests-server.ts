import { execFile } from 'node:child_process';
import path from 'node:path';
import { promisify } from 'node:util';
import 'server-only';
import type { HelpRequest, HelpRequestStatus, HelpRequestUrgency } from './help-requests';

const execFileAsync = promisify(execFile);
const backendDir = path.join(process.cwd(), '../backend');
const python = process.env.HELP_REQUESTS_PYTHON ?? path.join(backendDir, '.venv/bin/python');
const script = path.join(backendDir, 'src/help_requests_cli.py');
const database = process.env.HELP_REQUESTS_DB_PATH ?? path.join(backendDir, 'memory.db');

interface ListPayload {
  requests: HelpRequest[];
}

interface UpdatePayload {
  request: HelpRequest;
}

async function runBridge(arguments_: string[]): Promise<unknown> {
  const { stdout } = await execFileAsync(python, [script, ...arguments_, '--db-path', database], {
    cwd: backendDir,
    encoding: 'utf8',
    maxBuffer: 1024 * 1024,
  });
  return JSON.parse(stdout) as unknown;
}

export async function listHelpRequests(filters: {
  status?: HelpRequestStatus;
  urgency?: HelpRequestUrgency;
}): Promise<HelpRequest[]> {
  const arguments_ = ['list'];
  if (filters.status) arguments_.push('--status', filters.status);
  if (filters.urgency) arguments_.push('--urgency', filters.urgency);
  const payload = (await runBridge(arguments_)) as ListPayload;
  if (!Array.isArray(payload.requests)) {
    throw new Error('Invalid help-request bridge response.');
  }
  return payload.requests;
}

export async function setHelpRequestStatus(
  referenceId: string,
  status: HelpRequestStatus
): Promise<HelpRequest> {
  const payload = (await runBridge([
    'update',
    '--reference-id',
    referenceId,
    '--status',
    status,
  ])) as UpdatePayload;
  if (!payload.request) {
    throw new Error('Invalid help-request bridge response.');
  }
  return payload.request;
}
