import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createDatabase } from '../src/database.js';
import { migrate } from '../src/migrate.js';
import { buildApp } from '../src/app.js';
import { apiToken, syncToken, chain, analysis, syncHeaders, headers } from './helpers.js';

// O CI fornece um banco descartavel exclusivo. Nunca aponte TEST_DATABASE_URL para producao.
test('driver pg: conexao, transacao, HTTP e persistencia em PostgreSQL', {
  skip: !process.env.TEST_DATABASE_URL,
}, async () => {
  const db = createDatabase(process.env.TEST_DATABASE_URL!, false);
  const app = buildApp({ db, apiToken, syncToken });
  try {
    await migrate(db);
    await assert.rejects(db.transaction(async (connection) => {
      await connection.query(`INSERT INTO public.lot (name) VALUES ('rollback-do-driver')`);
      throw new Error('rollback intencional');
    }), /rollback intencional/);
    assert.equal((await db.query(`SELECT count(*)::int AS count FROM public.lot
      WHERE name = 'rollback-do-driver'`)).rows[0].count, 0);
    const data = await chain(app);
    assert.equal(data.lot.age_reference_date, '2026-11-01');
    const item = analysis(undefined, String(data.camera.id));
    const received = await app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders,
      payload: { schema_version: 1, analyses: [item] } });
    assert.deepEqual(received.json(), { accepted_analysis_ids: [item.analise_id], rejected: [] });
    assert.equal((await app.inject({ url: `/analyses/${item.analise_id}`, headers })).json().visible_birds, 23);
  } finally { await app.close(); }
});
