import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/** Web liveness probe used by the docker-compose healthcheck. */
export async function GET() {
  return NextResponse.json({ status: 'ok', service: 'avsar-web' });
}
