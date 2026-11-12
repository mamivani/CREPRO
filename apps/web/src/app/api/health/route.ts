import { NextResponse } from 'next/server';

// Liveness/readiness target for the Container App probes (apps.tf) and the
// deploy workflow's post-apply smoke test.
export async function GET() {
  return NextResponse.json({ status: 'ok' });
}
