'use client';

/**
 * Microphone capture for one conversational turn.
 *
 * TECH_STACK.md §4 fixes the contract: **16 kHz mono WAV, <=15 s per turn**.
 * MediaRecorder gives us WebM/Opus at the device's native rate, so this module
 * decodes, downmixes to mono, resamples to 16 kHz with an OfflineAudioContext
 * and encodes a PCM WAV itself. Doing the conversion client-side keeps the
 * server contract identical for PWA, recorded audio and IVR (ARCHITECTURE §2
 * invariant 4: "One brain, many ears").
 */

export const SAMPLE_RATE = 16_000;
export const MAX_SECONDS = 15;

export type RecorderHandle = {
  stop: () => Promise<string>;
  cancel: () => void;
  stream: MediaStream;
};

export function isRecordingSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined'
  );
}

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined;
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type));
}

/** Downmix to mono and resample to 16 kHz. */
async function toMono16k(buffer: ArrayBuffer): Promise<Float32Array> {
  const Ctx: typeof AudioContext =
    (window as any).AudioContext ?? (window as any).webkitAudioContext;
  const decodeCtx = new Ctx();
  let decoded: AudioBuffer;
  try {
    decoded = await decodeCtx.decodeAudioData(buffer.slice(0));
  } finally {
    void decodeCtx.close();
  }

  const targetLength = Math.max(1, Math.ceil((decoded.duration * SAMPLE_RATE) || 1));
  const OfflineCtx: typeof OfflineAudioContext =
    (window as any).OfflineAudioContext ?? (window as any).webkitOfflineAudioContext;
  const offline = new OfflineCtx(1, targetLength, SAMPLE_RATE);

  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start(0);

  const rendered = await offline.startRendering();
  return rendered.getChannelData(0);
}

/** Encode mono float samples as a 16-bit PCM WAV. */
function encodeWav(samples: Float32Array, sampleRate = SAMPLE_RATE): Uint8Array {
  const bytes = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(bytes);

  const writeString = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // PCM chunk size
  view.setUint16(20, 1, true); // format = PCM
  view.setUint16(22, 1, true); // channels = mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += 2;
  }
  return new Uint8Array(bytes);
}

function toBase64(bytes: Uint8Array): string {
  let binary = '';
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return btoa(binary);
}

/**
 * Start recording. Resolves with a handle; `stop()` returns base64 WAV.
 * Auto-stops at MAX_SECONDS so a turn can never exceed the server limit.
 */
export async function startRecording(onAutoStop?: () => void): Promise<RecorderHandle> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      // Browser AEC/NS, per ARCHITECTURE §6 ("echo-cancel via browser AEC").
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  const mimeType = pickMimeType();
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  const chunks: BlobPart[] = [];
  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  };
  recorder.start();

  let stopped = false;
  const timer = window.setTimeout(() => {
    if (recorder.state === 'recording') {
      recorder.stop();
      onAutoStop?.();
    }
  }, MAX_SECONDS * 1000);

  const release = () => {
    window.clearTimeout(timer);
    stream.getTracks().forEach((track) => track.stop());
  };

  return {
    stream,
    cancel: () => {
      stopped = true;
      if (recorder.state !== 'inactive') recorder.stop();
      release();
    },
    stop: () =>
      new Promise<string>((resolve, reject) => {
        if (stopped) {
          reject(new Error('recording cancelled'));
          return;
        }
        recorder.onstop = async () => {
          release();
          try {
            const blob = new Blob(chunks, { type: mimeType ?? 'audio/webm' });
            const samples = await toMono16k(await blob.arrayBuffer());
            const capped = samples.subarray(0, SAMPLE_RATE * MAX_SECONDS);
            resolve(toBase64(encodeWav(capped)));
          } catch (error) {
            reject(error);
          }
        };
        if (recorder.state === 'recording') recorder.stop();
        else recorder.onstop?.(new Event('stop'));
      }),
  };
}

/** Sequential playback of streamed TTS chunks, with barge-in support. */
export class TtsPlayer {
  private queue: string[] = [];
  private audio: HTMLAudioElement | null = null;
  private playing = false;
  onEnded?: () => void;

  enqueue(base64: string, mime = 'audio/wav') {
    this.queue.push(`data:${mime};base64,${base64}`);
    if (!this.playing) void this.drain();
  }

  private async drain() {
    this.playing = true;
    while (this.queue.length > 0) {
      const src = this.queue.shift()!;
      await new Promise<void>((resolve) => {
        const audio = new Audio(src);
        this.audio = audio;
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
        audio.play().catch(() => resolve());
      });
    }
    this.playing = false;
    this.audio = null;
    this.onEnded?.();
  }

  /** Barge-in: any user speech interrupts TTS (ARCHITECTURE §6). */
  stop() {
    this.queue = [];
    if (this.audio) {
      this.audio.pause();
      this.audio = null;
    }
    this.playing = false;
  }

  get isPlaying() {
    return this.playing;
  }
}
