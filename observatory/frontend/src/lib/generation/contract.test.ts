import { describe, expect, it } from 'vitest';
import {
  CONTRACT_VERSION,
  FORBIDDEN_PUBLIC_FIELDS,
  SOCIAL_API_CAPABILITY,
  SOCIAL_API_ORIGIN,
  assertSafePublicStatus,
  type GenerationJobStatus,
} from './contract';

describe('holus.generation.v1 contract', () => {
  it('pins the versioned public surface', () => {
    expect(CONTRACT_VERSION).toBe('holus.generation.v1');
    expect(SOCIAL_API_ORIGIN).toBe('https://api.camilomartinez.co/');
    expect(SOCIAL_API_CAPABILITY).toContain('X, Threads, Instagram, Facebook, and LinkedIn');
  });

  it('rejects forbidden operator fields on public status', () => {
    const status = {
      contract_version: CONTRACT_VERSION,
      request_id: 'holus-demo-1',
      job_id: 'holus-mapped-1',
      status: 'ready',
      stage: 'ready',
      progress: 1,
      user_message: 'ok',
      preview: { availability: 'local_placeholder', label: 'Local placeholder' },
      source: 'demo',
      cost_usd: 1.2,
    } as GenerationJobStatus & { cost_usd: number };

    expect(() => assertSafePublicStatus(status)).toThrow(/Forbidden public field/);
    expect(FORBIDDEN_PUBLIC_FIELDS).toContain('cost_usd');
    expect(FORBIDDEN_PUBLIC_FIELDS).toContain('trace');
    expect(FORBIDDEN_PUBLIC_FIELDS).toContain('artifact_url');
    expect(FORBIDDEN_PUBLIC_FIELDS).toContain('credentials');
  });
});
