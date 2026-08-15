import { NextResponse } from 'next/server';
import { isHelpRequestStatus } from '@/lib/help-requests';
import { setHelpRequestStatus } from '@/lib/help-requests-server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const REFERENCE_PATTERN = /^KS-\d{8}-[A-F0-9]{4}$/;

interface RouteContext {
  params: Promise<{ referenceId: string }>;
}

export async function PATCH(request: Request, context: RouteContext) {
  const { referenceId } = await context.params;
  if (!REFERENCE_PATTERN.test(referenceId)) {
    return NextResponse.json({ error: 'Invalid help-request reference.' }, { status: 400 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
  }

  const status =
    typeof body === 'object' && body !== null && 'status' in body ? body.status : undefined;
  if (!isHelpRequestStatus(status)) {
    return NextResponse.json({ error: 'Invalid status.' }, { status: 400 });
  }

  try {
    const updated = await setHelpRequestStatus(referenceId, status);
    return NextResponse.json({ request: updated });
  } catch (error) {
    const code =
      typeof error === 'object' && error !== null && 'code' in error && error.code === 1
        ? 404
        : 500;
    return NextResponse.json(
      {
        error:
          code === 404 ? 'Help request was not found.' : 'Help requests are unavailable right now.',
      },
      { status: code }
    );
  }
}
