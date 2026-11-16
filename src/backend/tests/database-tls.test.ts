import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Client } from 'pg';
import { databasePoolConfig } from '../src/database.js';
import { loadConfig } from '../src/config.js';

for (const parameter of ['ssl=0', 'ssl=no-verify']) {
  test(`DATABASE_SSL=true prevalece sobre ${parameter} no driver pg`, () => {
    const settings = loadConfig({
      DATABASE_URL: `postgresql://user:password@database.example/raiar?${parameter}`,
      DATABASE_SSL: 'true', RAIAR_API_TOKEN: 'a'.repeat(32), RAIAR_SYNC_TOKEN: 'b'.repeat(32),
    });
    const client = new Client(databasePoolConfig(settings.DATABASE_URL, settings.DATABASE_SSL));
    // Conferir o resultado do parser real do driver, nao apenas o objeto entregue ao pool.
    assert.deepEqual(client.ssl, { rejectUnauthorized: true });
  });
}

test('remove aliases, repeticoes e parametros de certificado sem perder as demais opcoes', () => {
  const url = 'postgresql://user:p%40ss@database.example:5433/raiar'
    + '?ssl=0&ssl=no-verify&sslmode=disable&sslrootcert=inexistente&sslkey=inexistente'
    + '&sslcert=inexistente&sslnegotiation=direct&uselibpqcompat=true&%73sl=no-verify'
    + '&application_name=raiar-teste';
  const client = new Client(databasePoolConfig(url, true));
  assert.deepEqual(client.ssl, { rejectUnauthorized: true });
  assert.equal(client.host, 'database.example');
  assert.equal(client.port, 5433);
  assert.equal(client.database, 'raiar');
  assert.equal(client.password, 'p@ss');
  const sanitized = new URL(databasePoolConfig(url, true).connectionString!);
  assert.deepEqual([...sanitized.searchParams.entries()], [['application_name', 'raiar-teste']]);
});

test('DATABASE_SSL=false controla exclusivamente a conexao local', () => {
  const client = new Client(databasePoolConfig('postgresql://user:pass@localhost/raiar?ssl=no-verify', false));
  assert.equal(client.ssl, false);
});

for (const parameter of ['host=database.example', '%68ost=database.example',
  'host=localhost&host=database.example', 'hostaddr=203.0.113.1']) {
  test(`recusa sobrescrita do destino por ${parameter}`, () => {
    const url = `postgresql://user:password@localhost/raiar?${parameter}`;
    assert.throws(() => loadConfig({
      DATABASE_URL: url, DATABASE_SSL: 'false',
      RAIAR_API_TOKEN: 'a'.repeat(32), RAIAR_SYNC_TOKEN: 'b'.repeat(32),
    }), /DATABASE_URL/);
    for (const ssl of [true, false]) {
      assert.throws(() => databasePoolConfig(url, ssl), /host/);
    }
  });
}

test('o pool tambem recusa conexao remota sem TLS quando usado sem loadConfig', () => {
  assert.throws(() => databasePoolConfig('postgresql://user:password@database.example/raiar', false), /TLS/);
  const client = new Client(databasePoolConfig('postgresql://user:password@database.example/raiar', true));
  assert.equal(client.host, 'database.example');
  assert.deepEqual(client.ssl, { rejectUnauthorized: true });
});
