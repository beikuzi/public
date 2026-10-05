import { open, stat, unlink } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { translateBatch } from './batch.mjs';
import { BatchError } from './adapter.mjs';
const allowed = new Set(['--input','--output','--model','--target','--max-calls','--max-characters','--timeout-ms','--allow-paid-remote']);
const MAX_INPUT_BYTES = 300000;

export async function readBoundedInput(path) {
  const file = await open(path, 'r');
  try {
    const info = await file.stat();
    if (!info.isFile()) throw new BatchError('INPUT_MUST_BE_FILE');
    if (info.size > MAX_INPUT_BYTES) throw new BatchError('INPUT_TOO_LARGE');
    // Read at most limit + 1 even if another process grows the file after stat().
    const buffer = Buffer.alloc(MAX_INPUT_BYTES + 1);
    let length = 0;
    while (length < buffer.length) {
      const { bytesRead } = await file.read(buffer, length, buffer.length - length, null);
      if (!bytesRead) break;
      length += bytesRead;
    }
    if (length > MAX_INPUT_BYTES) throw new BatchError('INPUT_TOO_LARGE');
    return JSON.parse(buffer.subarray(0, length).toString('utf8'));
  } finally { await file.close(); }
}

export async function executeCLI(args, { batch = translateBatch, signal } = {}) {
  const opts = {};
  for (let i = 0; i < args.length; i++) {
    const key = args[i];
    if (!allowed.has(key) || Object.hasOwn(opts, key)) throw new BatchError('INVALID_ARGUMENTS');
    opts[key] = key === '--allow-paid-remote' ? true : args[++i];
    if (opts[key] === undefined || (typeof opts[key] === 'string' && opts[key].startsWith('--'))) throw new BatchError('INVALID_ARGUMENTS');
  }
  if (!opts['--input'] || !opts['--output']) throw new BatchError('INPUT_OUTPUT_REQUIRED');
  const input = await readBoundedInput(opts['--input']);
  // Reserve the actual output handle before any SDK import or possibly billed run.
  // wx also rejects existing files/symlinks, and opening tests directory permissions.
  const output = await open(opts['--output'], 'wx', 0o600);
  const identity = await output.stat();
  let completed = false;
  try {
    const number = key => opts[key] === undefined ? undefined : Number(opts[key]);
    const result = await batch(input, {
      target: opts['--target'], model: opts['--model'], maxCalls: number('--max-calls'),
      maxCharacters: number('--max-characters'), timeoutMs: number('--timeout-ms'),
      allowPaidRemote: opts['--allow-paid-remote'] === true, signal,
    });
    await output.writeFile(JSON.stringify(result, null, 2) + '\n');
    await output.sync();
    completed = true;
    return { total: result.results.length, errors: result.results.filter(item => item.status === 'error').length };
  } finally {
    await output.close();
    if (!completed) {
      // Do not remove a replacement created by another process.
      const current = await stat(opts['--output']).catch(() => null);
      if (current?.ino === identity.ino && current?.dev === identity.dev && current.size === 0) await unlink(opts['--output']).catch(() => {});
    }
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  process.on('SIGINT', abort); process.on('SIGTERM', abort);
  try {
    const summary = await executeCLI(process.argv.slice(2), { signal: controller.signal });
    console.error(JSON.stringify(summary));
    process.exitCode = summary.errors ? 2 : 0;
  } catch (error) {
    console.error(error instanceof BatchError ? error.code : 'LOCAL_IO_OR_INPUT_FAILURE');
    process.exitCode = 1;
  } finally {
    process.removeListener('SIGINT', abort); process.removeListener('SIGTERM', abort);
  }
}
