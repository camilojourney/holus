/**
 * Honest Holus connection state for public/demo surfaces.
 *
 * Live events require an authenticated backend. Public pages must never
 * open EventSource (or any other client) against localhost.
 */

export type ConnectionKind = 'demo' | 'connection_required' | 'local_dev';

export interface ConnectionState {
  kind: ConnectionKind;
  label: 'Demo data' | 'Connection required' | 'Local development';
  liveEventsAllowed: boolean;
  generationTransport: 'local-demo' | 'unavailable';
  detail: string;
}

export interface ConnectionContext {
  hostname?: string;
  demoMode?: boolean;
  nodeEnv?: string;
  observatoryUrl?: string;
  liveEvents?: boolean;
}

function readHostname(explicit?: string): string {
  if (explicit !== undefined) return explicit;
  if (typeof window === 'undefined') return '';
  return window.location.hostname;
}

export function isLocalDevHost(hostname: string): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
}

export function isLocalhostApiUrl(url: string): boolean {
  return /localhost|127\.0\.0\.1|\[::1\]/i.test(url);
}

function envFlag(name: string): boolean {
  return process.env[name] === 'true';
}

export function resolveConnection(ctx: ConnectionContext = {}): ConnectionState {
  const demoMode = ctx.demoMode ?? envFlag('NEXT_PUBLIC_DEMO_MODE');
  const liveEvents = ctx.liveEvents ?? envFlag('NEXT_PUBLIC_LIVE_EVENTS');
  const nodeEnv = ctx.nodeEnv ?? process.env.NODE_ENV ?? 'development';
  const observatoryUrl =
    ctx.observatoryUrl ??
    process.env.NEXT_PUBLIC_OBSERVATORY_URL ??
    'http://localhost:8003';
  const hostname = readHostname(ctx.hostname);

  const publicHost = hostname !== '' && !isLocalDevHost(hostname);
  const productionLocalApi = nodeEnv === 'production' && isLocalhostApiUrl(observatoryUrl);

  if (demoMode || publicHost || productionLocalApi) {
    return {
      kind: demoMode ? 'demo' : 'connection_required',
      label: demoMode ? 'Demo data' : 'Connection required',
      liveEventsAllowed: false,
      generationTransport: 'local-demo',
      detail:
        'Live events require an authenticated backend connection. This surface uses a local demonstration adapter and does not create a generation job.',
    };
  }

  if (!liveEvents && isLocalhostApiUrl(observatoryUrl) && !isLocalDevHost(hostname) && hostname !== '') {
    return {
      kind: 'connection_required',
      label: 'Connection required',
      liveEventsAllowed: false,
      generationTransport: 'unavailable',
      detail: 'Live events require an authenticated backend connection.',
    };
  }

  return {
    kind: 'local_dev',
    label: 'Local development',
    liveEventsAllowed: liveEvents || isLocalDevHost(hostname) || hostname === '',
    generationTransport: 'local-demo',
    detail: 'Local Observatory development. Generation remains a local demonstration until a Holus BFF is connected.',
  };
}

export function isPublicOrDemoSurface(ctx: ConnectionContext = {}): boolean {
  const state = resolveConnection(ctx);
  return state.kind !== 'local_dev';
}

export function allowsLiveEventStream(ctx: ConnectionContext = {}): boolean {
  return resolveConnection(ctx).liveEventsAllowed;
}

/**
 * SSE URL for live trajectory events.
 * Returns null when the client must not connect — including any case that
 * would target localhost from a public page.
 */
export function trajectoryStreamUrl(ctx: ConnectionContext = {}): string | null {
  if (!allowsLiveEventStream(ctx)) return null;
  const hostname = readHostname(ctx.hostname);
  if (hostname !== '' && !isLocalDevHost(hostname)) return null;
  const observatoryUrl =
    ctx.observatoryUrl ??
    process.env.NEXT_PUBLIC_OBSERVATORY_URL ??
    'http://localhost:8003';
  if (typeof window === 'undefined') {
    if (isLocalhostApiUrl(observatoryUrl) && process.env.NODE_ENV === 'production') {
      return null;
    }
    return `${observatoryUrl}/api/v1/trajectory/stream`;
  }
  if (isLocalhostApiUrl(observatoryUrl) && !isLocalDevHost(hostname)) {
    return null;
  }
  return '/api/v1/trajectory/stream';
}
