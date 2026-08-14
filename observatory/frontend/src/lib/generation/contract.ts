/**
 * Holus-owned public generation contract, version holus.generation.v1.
 *
 * Future authenticated BFF surface, limited to:
 *   - create a generation request
 *   - read one Holus-mapped job's restricted status
 *   - obtain a preview reference (never an artifact URL)
 *
 * Explicitly excluded: costs, raw traces, artifacts, review, rejection,
 * delivery, publishing, credentials, and operator controls.
 */

export const CONTRACT_VERSION = 'holus.generation.v1' as const;

export const SOCIAL_API_ORIGIN = 'https://api.camilomartinez.co/';
export const SOCIAL_API_OPENAPI = 'https://api.camilomartinez.co/openapi.json';
export const SOCIAL_API_CAPABILITY =
  'A versioned API for authenticated teams to publish, schedule, and manage social content across X, Threads, Instagram, Facebook, and LinkedIn from one integration.';

export type PublicGenerationStatus = 'queued' | 'generating' | 'ready' | 'error';
export type GenerationSource = 'demo' | 'connection_required' | 'bff';
export type PreviewAvailability = 'unavailable' | 'local_placeholder';
export type GenerationMode = 'preview';

export const FORBIDDEN_PUBLIC_FIELDS = [
  'cost',
  'costs',
  'cost_usd',
  'trace',
  'traces',
  'raw_trace',
  'artifact',
  'artifacts',
  'artifact_url',
  'review',
  'rejection',
  'reject',
  'delivery',
  'publish',
  'publishing',
  'credentials',
  'api_key',
  'operator',
  'operator_controls',
] as const;

export interface CreateGenerationRequest {
  instruction: string;
  niche?: string;
  target_platform?: string;
  mode?: GenerationMode;
}

export interface PreviewReference {
  availability: PreviewAvailability;
  label: string;
}

export interface CreateGenerationResponse {
  contract_version: typeof CONTRACT_VERSION;
  request_id: string;
  job_id: string;
  status: PublicGenerationStatus;
  source: GenerationSource;
}

export interface GenerationJobStatus {
  contract_version: typeof CONTRACT_VERSION;
  request_id: string;
  job_id: string;
  status: PublicGenerationStatus;
  stage: string | null;
  progress: number | null;
  user_message: string | null;
  preview: PreviewReference;
  source: GenerationSource;
}

export const PUBLIC_STATUS_FIELDS: (keyof GenerationJobStatus)[] = [
  'contract_version',
  'request_id',
  'job_id',
  'status',
  'stage',
  'progress',
  'user_message',
  'preview',
  'source',
];

export function assertSafePublicStatus(status: GenerationJobStatus): void {
  const keys = Object.keys(status);
  for (const key of keys) {
    if ((FORBIDDEN_PUBLIC_FIELDS as readonly string[]).includes(key)) {
      throw new Error(`Forbidden public field: ${key}`);
    }
  }
  if ('url' in (status.preview as object)) {
    throw new Error('Preview must not include a URL');
  }
}

export const DEMO_REQUEST: CreateGenerationRequest = {
  instruction:
    'Demonstrate a short product explainer from a private generation capability, orchestrated by Holus.',
  niche: 'Recruiter product demo',
  target_platform: 'linkedin',
  mode: 'preview',
};
