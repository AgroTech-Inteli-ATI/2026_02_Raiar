import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { migrate, transactionBody } from '../src/migrate.js';
import { testDatabase } from './helpers.js';
import { loadConfig } from '../src/config.js';

test('migra uma base nova, preserva dados na repeticao e verifica checksums', async () => {
  const db = testDatabase();
  try {
    const applied = await migrate(db);
    assert.equal(applied.length, 4);
    await db.query(`INSERT INTO public.raspberry (name, hostname, active) VALUES ('RPi', 'teste', false)`);
    assert.deepEqual(await migrate(db), []);
    assert.equal((await db.query('SELECT active FROM public.raspberry')).rows[0].active, false);
    const sql = await readFile(new URL('../../database/tests/dados_cadastro.sql', import.meta.url), 'utf8');
    await db.query(sql);
    await db.query(`UPDATE backend_internal.migration SET checksum = 'divergente' WHERE name = '003_dados_cadastro.sql'`);
    await assert.rejects(migrate(db), /Migracao aplicada foi alterada/);
  } finally { await db.close(); }
});

test('adota a integracao existente sem recriar tabelas ou apagar analises', async () => {
  const db = testDatabase();
  try {
    const root = new URL('../../database/', import.meta.url);
    await db.query(transactionBody(await readFile(new URL('schema.sql', root), 'utf8')));
    await db.query(transactionBody(await readFile(new URL('migrations/002_analises.sql', root), 'utf8')));
    const applied = await migrate(db);
    assert.ok(applied.includes('002_analises.sql (existente)'));
    assert.equal(applied.length, 3);
  } finally { await db.close(); }
});

test('interrompe esquema parcial sem deixar registro de migracao aplicado', async () => {
  const db = testDatabase();
  try {
    await db.query('CREATE TABLE public.camera (id integer PRIMARY KEY)');
    await assert.rejects(migrate(db), /Esquema inicial incompleto/);
    const result = await db.query(`SELECT to_regclass('backend_internal.migration') AS ledger`);
    assert.equal(result.rows[0].ledger, null);
  } finally { await db.close(); }
});

test('valida configuracao sem imprimir segredos e exige TLS no banco remoto', () => {
  const valid = {
    DATABASE_URL: 'postgresql://user:password@localhost:5432/raiar', DATABASE_SSL: 'false',
    RAIAR_API_TOKEN: 'a'.repeat(32), RAIAR_SYNC_TOKEN: 'b'.repeat(32),
  };
  assert.equal(loadConfig(valid).PORT, 3000);
  assert.equal(loadConfig(valid).DATABASE_SSL, false);
  assert.throws(() => loadConfig({ ...valid, DATABASE_URL: 'postgresql://user:password@remote:5432/raiar' }), /DATABASE_SSL/);
  assert.throws(() => loadConfig({ ...valid, RAIAR_SYNC_TOKEN: valid.RAIAR_API_TOKEN }), /RAIAR_SYNC_TOKEN/);
  assert.throws(() => loadConfig({ ...valid, SUPABASE_URL: 'https://example.supabase.co' }), /SUPABASE_URL/);
  assert.throws(() => loadConfig({ ...valid, DATABASE_URL: 'senha-secreta' }), (error: unknown) =>
    error instanceof Error && !error.message.includes('senha-secreta'));
});
