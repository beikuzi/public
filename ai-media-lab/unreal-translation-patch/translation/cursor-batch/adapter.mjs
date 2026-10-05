import { mkdtemp, mkdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export class BatchError extends Error {
  constructor(code) { super(code); this.code = code; }
}
const fail = code => { throw new BatchError(code); };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

/** No SDK import or network activity until explicitly opted in. SDK is injectable for tests. */
export async function runTextOnly(prompt, {
  sdk, apiKey = process.env.CURSOR_API_KEY, model,
  allowPaidRemote = false, timeoutMs = 120000, signal,
} = {}) {
  if (!allowPaidRemote) fail('REMOTE_OPT_IN_REQUIRED');
  if (process.env.CURSOR_BACKEND_URL || process.env.CURSOR_WEBSITE_URL) fail('ENDPOINT_OVERRIDE_FORBIDDEN');
  if (typeof apiKey !== 'string' || !apiKey.trim()) fail('KEY_REQUIRED');
  if (typeof model !== 'string' || !/^[A-Za-z0-9_.-]{1,100}$/.test(model) || model === 'auto-smart') fail('EXPLICIT_FIXED_MODEL_REQUIRED');
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 600000) fail('INVALID_TIMEOUT');
  if (typeof prompt !== 'string' || Buffer.byteLength(prompt) > 100000) fail('PROMPT_TOO_LARGE');
  if (signal?.aborted) fail('CANCELLED');
  const [major, minor] = process.versions.node.split('.').map(Number);
  if (major < 22 || (major === 22 && minor < 13)) fail('NODE_22_13_REQUIRED');
  let root, agent, run, stopped = false, timer, onAbort;
  // Late SDK operations are observed and stopped; never resend a possibly billed request.
  const cancel = async () => { try { await run?.cancel(); } catch {} };
  const dispose = async () => {
    try {
      if (agent?.[Symbol.asyncDispose]) await agent[Symbol.asyncDispose]();
      else agent?.close();
    } catch {}
  };
  const stop = async () => { await Promise.race([cancel(), delay(1000)]); await Promise.race([dispose(), delay(1000)]); };
  const deadline = new Promise((_, reject) => {
    timer = setTimeout(() => { stopped = true; reject(new BatchError('TIMEOUT')); }, timeoutMs);
    onAbort = () => { stopped = true; reject(new BatchError('CANCELLED')); };
    signal?.addEventListener('abort', onAbort, { once: true });
  });
  const operation = (async () => {
    sdk ??= await import('@cursor/sdk');
    if (stopped) fail('CANCELLED');
    root = await mkdtemp(join(tmpdir(), 'utp-cursor-'));
    const cwd = join(root, 'workspace');
    await mkdir(cwd, { mode: 0o700 });
    if (stopped) fail('CANCELLED');
    agent = await sdk.Agent.create({
      apiKey, model: { id: model }, tools: [], disallowedTools: ['mcp', 'task'],
      mcpServers: {}, agents: {},
      local: { cwd, settingSources: [], enableAgentRetries: false,
        store: new sdk.JsonlLocalAgentStore(join(root, 'state')) },
    });
    if (stopped) { await dispose(); fail('CANCELLED'); }
    run = await agent.send(prompt);
    if (stopped) { await stop(); fail('CANCELLED'); }
    // Toolset restrictions prevent execution. Stream checking is an additional fail-closed tripwire.
    const inspect = (async () => {
      for await (const event of run.stream()) {
        if (event.type === 'tool_call') { await cancel(); fail('UNEXPECTED_TOOL_CALL'); }
      }
    })();
    const [result] = await Promise.all([run.wait(), inspect]);
    if (result.status !== 'finished') fail(result.status === 'cancelled' ? 'CANCELLED' : 'RUN_NOT_FINISHED');
    if (typeof result.result !== 'string' || !result.result.trim()) fail('EMPTY_RESULT');
    if (Buffer.byteLength(result.result) > 200000) fail('RESULT_TOO_LARGE');
    return result.result;
  })();
  try { return await Promise.race([operation, deadline]); }
  catch (error) { throw error instanceof BatchError ? error : new BatchError('SDK_FAILURE'); }
  finally {
    stopped = true;
    clearTimeout(timer); signal?.removeEventListener('abort', onAbort);
    await stop();
    // Dispose before removal. If an operation completes late, repeat cleanup after it settles.
    const cleanup = async () => { if (root) await rm(root, { recursive: true, force: true }).catch(() => {}); };
    await cleanup();
    operation.then(cleanup, cleanup);
  }
}
