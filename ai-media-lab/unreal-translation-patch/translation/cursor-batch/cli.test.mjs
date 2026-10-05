import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, rm, access, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { executeCLI } from './cli.mjs';
const fixture = { version: 1, texts: [{ id: 'hello', text: 'Hello' }] };
async function workspace(fn) {
  const dir = await mkdtemp(join(tmpdir(), 'utp-cli-test-'));
  try { const input = join(dir, 'input.json'); await writeFile(input, JSON.stringify(fixture)); await fn(dir, input); }
  finally { await rm(dir, { recursive: true, force: true }); }
}
test('CLI existing output rejected before any SDK/batch invocation', () => workspace(async (dir, input) => {
  const output = join(dir, 'output.json'); await writeFile(output, 'keep');
  let calls = 0;
  await assert.rejects(executeCLI(['--input', input, '--output', output, '--allow-paid-remote'], { batch: async () => { calls++; } }), { code: 'EEXIST' });
  assert.equal(calls, 0); assert.equal(await readFile(output, 'utf8'), 'keep');
}));
test('CLI nonexistent destination parent rejected before SDK/batch invocation', () => workspace(async (dir, input) => {
  let calls = 0;
  await assert.rejects(executeCLI(['--input', input, '--output', join(dir, 'missing', 'out.json'), '--allow-paid-remote'], { batch: async () => { calls++; } }), { code: 'ENOENT' });
  assert.equal(calls, 0);
}));
test('CLI directory destination rejected before SDK/batch invocation', () => workspace(async (dir, input) => {
  let calls = 0;
  const output = join(dir, 'folder'); await mkdir(output);
  await assert.rejects(executeCLI(['--input', input, '--output', output, '--allow-paid-remote'], { batch: async () => { calls++; } }));
  assert.equal(calls, 0);
}));
test('CLI oversized input rejected before output reservation or SDK/batch invocation', () => workspace(async (dir, input) => {
  await writeFile(input, Buffer.alloc(300001, 32));
  let calls = 0; const output = join(dir, 'out.json');
  await assert.rejects(executeCLI(['--input', input, '--output', output, '--allow-paid-remote'], { batch: async () => { calls++; } }), /INPUT_TOO_LARGE/);
  assert.equal(calls, 0); await assert.rejects(access(output));
}));
test('CLI reserves writable destination before invoking batch and writes result', () => workspace(async (dir, input) => {
  const output = join(dir, 'out.json');
  const summary = await executeCLI(['--input', input, '--output', output], { batch: async received => {
    await access(output); assert.deepEqual(received, fixture);
    return { version: 1, results: [{ id: 'hello', text: '你好', status: 'translated' }] };
  } });
  assert.deepEqual(summary, { total: 1, errors: 0 });
  assert.equal(JSON.parse(await readFile(output, 'utf8')).results[0].text, '你好');
}));
test('CLI removes own empty reservation on validation failure', () => workspace(async (dir, input) => {
  const output = join(dir, 'out.json');
  await assert.rejects(executeCLI(['--input', input, '--output', output], { batch: async () => { throw new Error('mock failure'); } }), /mock failure/);
  await assert.rejects(access(output));
}));
