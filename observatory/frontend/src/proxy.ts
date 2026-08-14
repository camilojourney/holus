import { NextResponse, type NextRequest } from 'next/server';

function isPublicDemo(): boolean {
  return process.env.NODE_ENV === 'production' || process.env.NEXT_PUBLIC_DEMO_MODE === 'true';
}

export function proxy(request: NextRequest) {
  if (isPublicDemo()) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/agents',
    '/agents/:path*',
    '/evaluations',
    '/evaluations/:path*',
    '/results',
    '/results/:path*',
    '/knowledge',
    '/knowledge/:path*',
    '/engagement',
    '/engagement/:path*',
    '/followers',
    '/followers/:path*',
  ],
};
