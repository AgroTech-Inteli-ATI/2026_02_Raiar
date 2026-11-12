import assert from 'node:assert/strict';
import { mock, test } from 'node:test';
import { supabaseUserVerifier, tokensEqual } from '../src/auth.js';

test('valida JWT no Supabase e usa somente o papel de app_metadata', async () => {
  const responses = [
    { id: 'usuario-1', app_metadata: { role: 'gestor' } },
    { id: 'usuario-2', user_metadata: { role: 'gestor' } },
    { id: 'usuario-3', app_metadata: { role: 'desconhecido' } },
  ];
  const stub = mock.method(globalThis, 'fetch', async (url: URL, init: RequestInit) => {
    assert.equal(url.toString(), 'https://example.supabase.co/auth/v1/user');
    assert.equal((init.headers as Record<string, string>).Authorization, 'Bearer jwt-do-usuario');
    return new Response(JSON.stringify(responses.shift()), { status: 200 });
  });
  try {
    const verify = supabaseUserVerifier('https://example.supabase.co', 'chave-publicavel');
    assert.deepEqual(await verify('jwt-do-usuario'), { subject: 'usuario-1', role: 'gestor' });
    assert.equal(await verify('jwt-do-usuario'), null);
    assert.equal(await verify('jwt-do-usuario'), null);
  } finally { stub.mock.restore(); }
});

test('recusa JWT expirado e diferencia indisponibilidade do provedor', async () => {
  const stub = mock.method(globalThis, 'fetch', async () => new Response(null, { status: 401 }));
  try {
    const verify = supabaseUserVerifier('https://example.supabase.co', 'chave');
    assert.equal(await verify('expirado'), null);
    stub.mock.mockImplementation(async () => { throw new Error('rede indisponivel'); });
    await assert.rejects(verify('jwt'), { status: 503, code: 'auth_unavailable' });
  } finally { stub.mock.restore(); }
});

test('compara segredos completos, inclusive tamanhos distintos', () => {
  assert.equal(tokensEqual('abc', 'abc'), true);
  assert.equal(tokensEqual('abc', 'abcd'), false);
  assert.equal(tokensEqual('abc', 'abd'), false);
});
