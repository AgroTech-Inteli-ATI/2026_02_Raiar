import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { migrate, transactionBody } from '../src/migrate.js';
import { testDatabase } from './helpers.js';
import { loadConfig } from '../src/config.js';
import { analysis } from './helpers.js';

test('migra uma base nova, preserva dados na repeticao e verifica checksums', async () => {
  const db = testDatabase();
  try {
    const applied = await migrate(db);
    assert.equal(applied.length, 5);
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
    assert.equal(applied.length, 4);
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

test('adiciona historico a banco existente sem inventar ocupacao passada ou reescrever resultados', async () => {
  const db = testDatabase();
  try {
    const root = new URL('../../database/', import.meta.url);
    for (const file of ['schema.sql', 'migrations/002_analises.sql', 'migrations/003_dados_cadastro.sql',
      'migrations/004_ingestao_backend.sql']) {
      await db.query(transactionBody(await readFile(new URL(file, root), 'utf8')));
    }
    await db.query(`INSERT INTO public.raspberry (name, hostname) VALUES ('RPi', 'legado');
      INSERT INTO public.lot (name) VALUES ('Lote existente');
      INSERT INTO public.aviary (name, number, type, current_lot_id) VALUES ('Aviario', 1, 'rearing', 1);
      INSERT INTO public.camera (raspberry_id, aviary_id) VALUES (1, 1);`);
    const old = analysis();
    await db.query('SELECT public.ingest_analyses($1::jsonb)',
      [JSON.stringify({ schema_version: 1, analyses: [old] })]);
    const count = await db.query('SELECT count(*)::int AS count FROM public.analysis_level_count');
    assert.equal(count.rows[0].count, 2);

    const before = Date.now();
    await migrate(db);
    const history = await db.query('SELECT * FROM public.aviary_lot_assignment');
    assert.equal(history.rows.length, 1);
    assert.equal(history.rows[0].origin, 'migration_snapshot');
    const start = new Date(history.rows[0].started_at as string | Date).getTime();
    assert.ok(start >= before - 1000 && start <= Date.now());
    const saved = await db.query('SELECT * FROM public.analysis WHERE id = $1', [old.analise_id]);
    assert.equal(saved.rows[0].lot_id, 1);
    assert.equal(saved.rows[0].lot_assignment_id, null);
    assert.equal(saved.rows[0].lot_association_status, 'legacy_unverified');
    assert.deepEqual(saved.rows[0].payload, old);

    const late = { ...old, analise_id: '22222222-2222-4222-8222-222222222222',
      capturado_em: new Date(before - 60000).toISOString() };
    await db.query('SELECT public.ingest_analyses($1::jsonb)',
      [JSON.stringify({ schema_version: 1, analyses: [late] })]);
    const unknown = await db.query('SELECT lot_id, lot_association_status FROM public.analysis WHERE id = $1',
      [late.analise_id]);
    assert.equal(unknown.rows[0].lot_id, null);
    assert.equal(unknown.rows[0].lot_association_status, 'no_occupancy');
    assert.deepEqual(await migrate(db), []);
    assert.equal((await db.query('SELECT count(*)::int AS count FROM public.aviary_lot_assignment')).rows[0].count, 1);
  } finally { await db.close(); }
});

test('RPC administrativo nao herda EXECUTE publico dos default privileges do Supabase', async () => {
  const db = testDatabase();
  try {
    await db.query(`CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role;
      ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO anon, authenticated;`);
    await migrate(db);
    const { rows } = await db.query(`SELECT
      has_function_privilege('anon', 'public.assign_aviary_lot(integer,integer,timestamptz)', 'EXECUTE') AS anon,
      has_function_privilege('authenticated', 'public.assign_aviary_lot(integer,integer,timestamptz)', 'EXECUTE') AS authenticated,
      has_function_privilege('service_role', 'public.assign_aviary_lot(integer,integer,timestamptz)', 'EXECUTE') AS service`);
    assert.deepEqual(rows[0], { anon: false, authenticated: false, service: true });
  } finally { await db.close(); }
});
