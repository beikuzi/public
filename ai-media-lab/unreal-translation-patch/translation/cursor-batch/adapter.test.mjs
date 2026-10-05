import test from 'node:test';
import assert from 'node:assert/strict';
import { access } from 'node:fs/promises';
import { runTextOnly, BatchError } from './adapter.mjs';
import { translateBatch, prepare, validateResult } from './batch.mjs';
const input = { version: 1, texts: [{ id: 'welcome', text: 'Hello {PlayerName}!\n<Emphasis>Welcome</>' }] };
const opts = { allowPaidRemote: true, apiKey: 'mock-key-only', model: 'mock-model', timeoutMs: 200 };
function mock({ status = 'finished', result = '{}', events = [], hang = false, throwing = false } = {}) {
  const seen = { cancelled: 0, closed: 0, sends: 0 };
  const run = { cancel: async () => { seen.cancelled++; }, wait: async () => {
    if (throwing) throw new Error('secret upstream body');
    if (hang) return new Promise(() => {});
    return { status, result };
  }, stream: async function* () { yield* events; } };
  return { seen, sdk: { JsonlLocalAgentStore: class { constructor(path) { this.path = path; } }, Agent: { create: async options => {
    seen.options = options;
    return { send: async () => { seen.sends++; return run; }, [Symbol.asyncDispose]: async () => { seen.closed++; } };
  } } } };
}
test('text-only SDK options, final result, isolated cleanup', async () => {
  const m = mock({ result: 'hello' });
  assert.equal(await runTextOnly('test', { ...opts, sdk: m.sdk }), 'hello');
  assert.deepEqual(m.seen.options.tools, []);
  assert.deepEqual(m.seen.options.disallowedTools, ['mcp', 'task']);
  assert.deepEqual(m.seen.options.local.settingSources, []);
  assert.equal(m.seen.options.local.enableAgentRetries, false);
  assert.deepEqual(m.seen.options.mcpServers, {});
  assert.deepEqual(m.seen.options.agents, {});
  assert.equal(m.seen.sends, 1);
  await assert.rejects(access(m.seen.options.local.cwd));
});
test('no opt-in, missing key and endpoint overrides fail before SDK', async () => {
  const m = mock();
  await assert.rejects(runTextOnly('x', { ...opts, sdk: m.sdk, allowPaidRemote: false }), /REMOTE_OPT_IN_REQUIRED/);
  await assert.rejects(runTextOnly('x', { ...opts, sdk: m.sdk, apiKey: '' }), /KEY_REQUIRED/);
  const before = process.env.CURSOR_BACKEND_URL;
  process.env.CURSOR_BACKEND_URL = 'https://invalid.example';
  try { await assert.rejects(runTextOnly('x', { ...opts, sdk: m.sdk }), /ENDPOINT_OVERRIDE_FORBIDDEN/); }
  finally { if (before === undefined) delete process.env.CURSOR_BACKEND_URL; else process.env.CURSOR_BACKEND_URL = before; }
  assert.equal(m.seen.sends, 0);
});
for (const status of ['error', 'cancelled', 'running']) test(`reject partial ${status}`, async () => {
  const m = mock({ status, result: 'partial text' });
  await assert.rejects(runTextOnly('x', { ...opts, sdk: m.sdk }), status === 'cancelled' ? /CANCELLED/ : /RUN_NOT_FINISHED/);
});
test('tool attempt cancels and rejects', async () => {
  const m = mock({ events: [{ type: 'tool_call', name: 'shell' }] });
  await assert.rejects(runTextOnly('x', { ...opts, sdk: m.sdk }), /UNEXPECTED_TOOL_CALL/);
  assert.ok(m.seen.cancelled > 0);
});
test('timeout cancels; network failure is redacted and never retried', async () => {
  const m = mock({ hang: true });
  await assert.rejects(runTextOnly('x', { ...opts, sdk: m.sdk, timeoutMs: 5 }), /TIMEOUT/);
  assert.ok(m.seen.cancelled);
  const n = mock({ throwing: true });
  await assert.rejects(runTextOnly('x', { ...opts, sdk: n.sdk }), /SDK_FAILURE/);
  assert.equal(n.seen.sends, 1);
});
test('AbortSignal cancels run', async () => {
  const m = mock({ hang: true }), controller = new AbortController();
  const pending = runTextOnly('x', { ...opts, sdk: m.sdk, signal: controller.signal });
  setTimeout(() => controller.abort(), 10);
  await assert.rejects(pending, /CANCELLED/);
});
test('strict JSON preserves hash placeholders rich text', async () => {
  const runner = async prompt => {
    const data = JSON.parse(prompt.slice(prompt.indexOf('\n') + 1));
    data.text = data.text.replace('Hello', '你好').replace('Welcome', '欢迎');
    return JSON.stringify(data);
  };
  const out = await translateBatch(input, { ...opts, runner });
  assert.equal(out.results[0].text, '你好 {PlayerName}!\n<Emphasis>欢迎</>');
  assert.match(out.results[0].original_sha256, /^[a-f0-9]{64}$/);
  assert.equal(out.results[0].status, 'translated');
});
test('malformed output retains original and does not leak raw body', async () => {
  const out = await translateBatch(input, { ...opts, runner: async () => '```json\n{}\n```' });
  assert.equal(out.results[0].status, 'error'); assert.equal(out.results[0].text, input.texts[0].text);
  assert.equal(out.results[0].error, 'INVALID_JSON');
});
test('reject schema, hash, token reorder and invented markup', () => {
  const item = input.texts[0], p = prepare(item, 'zh-CN');
  for (const data of [{ ...p.payload, extra: true }, { ...p.payload, original_sha256: 'wrong' }, { ...p.payload, text: p.payload.text.replace(p.tokens[0], '') }, { ...p.payload, text: p.payload.text + '<New>' }]) {
    assert.throws(() => validateResult(JSON.stringify(data), item, p), BatchError);
  }
});
test('budget rejected before network, invalid ids rejected, nested ICU skipped', async () => {
  const runner = async () => { throw new Error('must not run'); };
  await assert.rejects(translateBatch(input, { ...opts, runner, maxCharacters: 1 }), /BATCH_BUDGET_EXCEEDED/);
  await assert.rejects(translateBatch({ version: 1, texts: [{ id: '../x', text: 'Hi' }] }, opts), /INVALID_INPUT/);
  const out = await translateBatch({ version: 1, texts: [{ id: 'icu', text: '{count, plural, one {cat} other {cats}}' }] }, { runner });
  assert.equal(out.results[0].status, 'skipped');
});
test('network failure stops remaining paid calls and keeps partial successes', async () => {
  let calls = 0;
  const texts = ['a', 'b', 'c', 'd'].map(id => ({ id, text: 'Hello' }));
  const runner = async prompt => {
    calls++; if (calls === 2) throw new BatchError('SDK_FAILURE');
    return JSON.stringify(JSON.parse(prompt.slice(prompt.indexOf('\n') + 1)));
  };
  const out = await translateBatch({ version: 1, texts }, { ...opts, runner });
  assert.equal(calls, 2); assert.equal(out.results[0].status, 'translated');
  assert.equal(out.results[2].error, 'BATCH_STOPPED');
});
