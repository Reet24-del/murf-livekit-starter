import { NextResponse } from 'next/server';
import { isHelpRequestStatus, isHelpRequestUrgency } from '@/lib/help-requests';
import { listHelpRequests } from '@/lib/help-requests-server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const rawStatus = searchParams.get('status');
  const rawUrgency = searchParams.get('urgency');

  if (rawStatus !== null && !isHelpRequestStatus(rawStatus)) {
    return NextResponse.json({ error: 'Invalid status filter.' }, { status: 400 });
  }
  if (rawUrgency !== null && !isHelpRequestUrgency(rawUrgency)) {
    return NextResponse.json({ error: 'Invalid urgency filter.' }, { status: 400 });
  }

  try {
    const requests = await listHelpRequests({
      status: rawStatus ?? undefined,
      urgency: rawUrgency ?? undefined,
    });
    return NextResponse.json({ requests });
  } catch {
    return NextResponse.json(
      { error: 'Help requests are unavailable right now.' },
      { status: 500 }
    );
  }
}
