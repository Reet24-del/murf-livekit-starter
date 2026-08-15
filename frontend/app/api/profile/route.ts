import { NextResponse } from 'next/server';
import { execFile } from 'child_process';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '../backend/memory.db');
const VALID_USER_ID = /^[a-zA-Z0-9_]+$/;

type CallerProfileSummary = {
  name: string | null;
  crops_grown: string | null;
  district: string | null;
  conversation_memory: string | null;
  last_interaction: string | null;
};

function readProfile(userId: string): Promise<CallerProfileSummary | null> {
  const sql = `SELECT name, crops_grown, district, conversation_memory, last_interaction FROM callers WHERE user_id = '${userId}' LIMIT 1;`;
  return new Promise((resolve, reject) => {
    execFile('sqlite3', ['-json', DB_PATH, sql], (error, stdout) => {
      if (error) {
        reject(error);
        return;
      }
      const rows = JSON.parse(stdout || '[]') as CallerProfileSummary[];
      resolve(rows[0] ?? null);
    });
  });
}

export async function GET(req: Request) {
  const userId = new URL(req.url).searchParams.get('user_id');
  if (!userId || !VALID_USER_ID.test(userId)) {
    return new NextResponse('Bad Request: Invalid user_id', { status: 400 });
  }

  try {
    const profile = await readProfile(userId);
    return profile
      ? NextResponse.json(profile)
      : new NextResponse('Profile not found', { status: 404 });
  } catch (error) {
    console.error('Failed to read profile:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const url = new URL(req.url);
    const userId = url.searchParams.get('user_id');

    if (!userId) {
      return new NextResponse('Bad Request: Missing user_id', { status: 400 });
    }

    // Safety check: validate user_id to prevent command/SQL injection
    if (!VALID_USER_ID.test(userId)) {
      return new NextResponse('Bad Request: Invalid user_id format', { status: 400 });
    }

    const sql = `DELETE FROM callers WHERE user_id = '${userId}';`;
    await new Promise<void>((resolve, reject) => {
      execFile('sqlite3', [DB_PATH, sql], (error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      });
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to reset memory:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
