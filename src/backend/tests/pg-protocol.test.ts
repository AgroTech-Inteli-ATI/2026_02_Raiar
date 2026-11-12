import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Pool } from 'pg';
import { PGlite } from '@electric-sql/pglite';
import { createPgConfig } from '@electric-sql/pglite/node-postgres';
import { databaseFromPool } from '../src/database.js';
import { migrate } from '../src/migrate.js';
import { buildApp } from '../src/app.js';
import { apiToken, syncToken, chain, analysis, syncHeaders } from './helpers.js';

test('pool pg e protocolo PostgreSQL: migracao, rollback e ingestao HTTP', async () => {
  const engine = new PGlite();
  const pool = new Pool({ ...createPgConfig(engine), max: 1 });
  const db = databaseFromPool(pool);
  const app = buildApp({ db, apiToken, syncToken });
  try {
    await migrate(db);
    await assert.rejects(db.transaction(async (connection) => {
      await connection.query(`INSERT INTO public.lot (name) VALUES ($1)`, ['reverter']);
      throw new Error('rollback intencional');
    }), /rollback intencional/);
    assert.equal((await db.query(`SELECT count(*)::int AS count FROM public.lot`)).rows[0].count, 0);
    const data = await chain(app);
    assert.equal(data.lot.age_reference_date, '2026-11-01');
    const item = analysis(undefined, String(data.camera.id));
    const send = () => app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders,
      payload: { schema_version: 1, analyses: [item] } });
    assert.deepEqual((await send()).json(), { accepted_analysis_ids: [item.analise_id], rejected: [] });
    assert.deepEqual((await send()).json().accepted_analysis_ids, [item.analise_id]);
    assert.equal((await db.query(`SELECT count(*)::int AS count FROM public.analysis`)).rows[0].count, 1);
    assert.deepEqual(await migrate(db), []);
  } finally {
    await app.close();
    await engine.close();
  }
});
