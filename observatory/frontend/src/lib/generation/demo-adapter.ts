/**
 * Local mock adapter for holus.generation.v1.
 * Satisfies the public contract without fetch, EventSource, secrets, or Genpeli.
 */

import {
  CONTRACT_VERSION,
  type CreateGenerationRequest,
  type CreateGenerationResponse,
  type GenerationJobStatus,
  type PreviewReference,
  type PublicGenerationStatus,
  assertSafePublicStatus,
} from './contract';

export interface DemoAdapterOptions {
  intervalMs?: number;
  idFactory?: () => string;
}

const QUEUED_MESSAGE =
  'Queued in the local Holus demo adapter. No live generation request was sent.';
const GENERATING_MESSAGE = 'Local demonstration is advancing. Genpeli was not contacted.';
const READY_MESSAGE =
  'Demonstration complete. Preview is a local placeholder, not a generated artifact.';
const ERROR_MESSAGE = 'Generation is unavailable in this demonstration. No live job was created.';

function unavailablePreview(): PreviewReference {
  return {
    availability: 'unavailable',
    label: 'Preview unavailable in this demonstration',
  };
}

function placeholderPreview(): PreviewReference {
  return {
    availability: 'local_placeholder',
    label: 'Local placeholder — not an artifact URL',
  };
}

function randomToken(): string {
  return Math.random().toString(16).slice(2, 14);
}

export class DemoGenerationAdapter {
  private readonly jobs = new Map<string, GenerationJobStatus>();
  private readonly outcomes = new Map<string, 'ready' | 'error'>();
  private readonly timers = new Set<ReturnType<typeof setTimeout>>();
  private readonly intervalMs: number;
  private readonly idFactory: () => string;

  constructor(options: DemoAdapterOptions = {}) {
    this.intervalMs = options.intervalMs ?? 700;
    this.idFactory = options.idFactory ?? randomToken;
  }

  create(
    _request: CreateGenerationRequest,
    outcome: 'ready' | 'error' = 'ready',
  ): CreateGenerationResponse {
    const token = this.idFactory();
    const request_id = `holus-demo-${token}`;
    const job_id = `holus-mapped-${token}`;
    const status: GenerationJobStatus = {
      contract_version: CONTRACT_VERSION,
      request_id,
      job_id,
      status: 'queued',
      stage: 'queued',
      progress: 0,
      user_message: QUEUED_MESSAGE,
      preview: unavailablePreview(),
      source: 'demo',
    };
    assertSafePublicStatus(status);
    this.jobs.set(request_id, status);
    this.outcomes.set(request_id, outcome);
    return {
      contract_version: CONTRACT_VERSION,
      request_id,
      job_id,
      status: 'queued',
      source: 'demo',
    };
  }

  get(requestId: string): GenerationJobStatus | undefined {
    return this.jobs.get(requestId);
  }

  subscribe(
    requestId: string,
    onChange: (status: GenerationJobStatus) => void,
  ): () => void {
    const current = this.jobs.get(requestId);
    if (current) onChange(current);

    const tick = () => {
      const next = this.advance(requestId);
      if (!next) return;
      onChange(next);
      if (next.status !== 'ready' && next.status !== 'error') {
        const handle = setTimeout(tick, this.intervalMs);
        this.timers.add(handle);
      }
    };

    if (this.intervalMs <= 0) {
      let status = this.jobs.get(requestId);
      while (status && status.status !== 'ready' && status.status !== 'error') {
        status = this.advance(requestId);
        if (status) onChange(status);
      }
      return () => undefined;
    }

    const handle = setTimeout(tick, this.intervalMs);
    this.timers.add(handle);
    return () => {
      this.timers.forEach((timer) => clearTimeout(timer));
      this.timers.clear();
    };
  }

  dispose(): void {
    this.timers.forEach((timer) => clearTimeout(timer));
    this.timers.clear();
  }

  private advance(requestId: string): GenerationJobStatus | undefined {
    const current = this.jobs.get(requestId);
    if (!current) return undefined;
    if (current.status === 'ready' || current.status === 'error') return current;

    const outcome = this.outcomes.get(requestId) ?? 'ready';
    let next: GenerationJobStatus;
    if (current.status === 'queued') {
      next = {
        ...current,
        status: 'generating',
        stage: 'generating',
        progress: 0.45,
        user_message: GENERATING_MESSAGE,
        preview: unavailablePreview(),
      };
    } else if (outcome === 'error') {
      next = {
        ...current,
        status: 'error',
        stage: 'error',
        progress: 0.45,
        user_message: ERROR_MESSAGE,
        preview: unavailablePreview(),
      };
    } else {
      next = {
        ...current,
        status: 'ready',
        stage: 'ready',
        progress: 1,
        user_message: READY_MESSAGE,
        preview: placeholderPreview(),
      };
    }
    assertSafePublicStatus(next);
    this.jobs.set(requestId, next);
    return next;
  }
}

export function isTerminalStatus(status: PublicGenerationStatus): boolean {
  return status === 'ready' || status === 'error';
}
