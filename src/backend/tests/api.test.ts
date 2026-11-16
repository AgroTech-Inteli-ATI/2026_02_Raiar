import assert from 'node:assert/strict';
import { after, before, beforeEach, describe, it } from 'node:test';
import { buildApp } from '../src/app.js';
import { setup, chain, analysis, headers, syncHeaders, apiToken, syncToken } from './helpers.js';
import type { Database } from '../src/database.js';

describe('API com PostgreSQL embarcado', { concurrency: false }, () => {
  let context: Awaited<ReturnType<typeof setup>>;
  before(async () => { context = await setup(); });
  after(async () => { await context?.app.close(); });
  beforeEach(async () => {
    await context.db.query(`TRUNCATE public.analysis_level_count, public.analysis, public.alerts,
      public.camera, public.aviary, public.lot, public.raspberry RESTART IDENTITY CASCADE`);
  });

  it('exige autenticacao e separa a credencial da API da sincronizacao', async () => {
    const { app } = context;
    assert.equal((await app.inject('/health')).statusCode, 200);
    assert.equal((await app.inject('/ready')).statusCode, 401);
    assert.equal((await app.inject({ url: '/ready', headers })).json().database, 'connected');
    assert.equal((await app.inject({ url: '/lots', headers: syncHeaders })).statusCode, 401);
    assert.equal((await app.inject({ method: 'POST', url: '/ingest-analyses', headers,
      payload: { schema_version: 1, analyses: [] } })).statusCode, 401);
    assert.equal((await app.inject({ url: '/me', headers })).json().role, 'gestor');
  });

  it('persiste os quatro cadastros e todos os campos aprovados', async () => {
    const { app } = context;
    const data = await chain(app);
    assert.equal(data.raspberry.active, true);
    assert.equal(data.camera.active, true);
    assert.equal(data.aviary.timezone, 'America/Sao_Paulo');
    assert.equal(data.lot.age_reference_date, '2026-11-01');
    assert.equal(data.lot.age_reference_source, 'Raiar');
    const response = await app.inject({ url: `/cameras/${data.camera.id}`, headers });
    assert.equal(response.json().name, 'Camera norte');
    assert.equal(response.json().aviary_id, data.aviary.id);
  });

  it('desativa e arquiva sem remover os registros ou seus vinculos', async () => {
    const { app } = context;
    await chain(app);
    for (const path of ['raspberries', 'cameras']) {
      const response = await app.inject({ method: 'PATCH', url: `/${path}/1`, headers, payload: { active: false } });
      assert.equal(response.statusCode, 200);
      assert.equal(response.json().active, false);
    }
    const archived = await app.inject({ method: 'PATCH', url: '/lots/1', headers,
      payload: { archived_at: '2026-11-12T10:00:00-03:00' } });
    assert.equal(new Date(archived.json().archived_at).toISOString(), '2026-11-12T13:00:00.000Z');
    assert.equal((await app.inject({ url: '/lots?archived=true', headers })).json().data.length, 1);
    assert.equal((await app.inject({ method: 'PATCH', url: '/lots/1', headers,
      payload: { archived_at: null } })).json().archived_at, null);
    assert.equal((await app.inject({ url: '/aviaries/1', headers })).json().current_lot_id, 1);
    assert.equal((await app.inject({ method: 'DELETE', url: '/lots/1', headers })).statusCode, 404);
  });

  it('valida idade, datas, fuso, campos extras e referencias', async () => {
    const { app } = context;
    await chain(app);
    for (const payload of [
      { name: 'Lote', age_days_reference: 4 },
      { name: 'Lote', age_days_reference: -1, age_reference_date: '2026-11-01', age_reference_source: 'Raiar' },
      { name: 'Lote', age_days_reference: 4, age_reference_date: '2026-02-30', age_reference_source: 'Raiar' },
      { name: 'Lote', id: 20 },
    ]) {
      assert.equal((await app.inject({ method: 'POST', url: '/lots', headers, payload })).statusCode, 422);
    }
    assert.equal((await app.inject({ method: 'PATCH', url: '/lots/1', headers,
      payload: { age_reference_source: null } })).statusCode, 422);
    assert.equal((await app.inject({ method: 'PATCH', url: '/lots/1', headers,
      payload: { age_days_reference: 11 } })).statusCode, 200);
    assert.equal((await app.inject({ method: 'PATCH', url: '/aviaries/1', headers,
      payload: { timezone: 'Fuso/Inexistente' } })).statusCode, 422);
    assert.equal((await app.inject({ method: 'POST', url: '/cameras', headers,
      payload: { raspberry_id: 999, aviary_id: 1 } })).statusCode, 409);
    assert.equal((await app.inject({ method: 'POST', url: '/raspberries', headers,
      payload: { name: 'Duplicado', hostname: 'raiar-1' } })).statusCode, 409);
    assert.equal((await app.inject({ method: 'PATCH', url: '/cameras/1', headers, payload: {} })).statusCode, 422);
    assert.equal((await app.inject({ url: '/cameras/999', headers })).statusCode, 404);
  });

  it('oferece filtros, paginacao e queries parametrizadas', async () => {
    const { app } = context;
    await chain(app);
    const maliciousName = "Camera'); DROP TABLE public.camera; --";
    assert.equal((await app.inject({ method: 'POST', url: '/cameras', headers,
      payload: { name: maliciousName, raspberry_id: 1, aviary_id: 1, active: false } })).statusCode, 201);
    const first = await app.inject({ url: '/cameras?limit=1&offset=0', headers });
    assert.equal(first.json().data.length, 1);
    assert.equal(first.json().pagination.has_more, true);
    const second = await app.inject({ url: '/cameras?limit=1&offset=1', headers });
    assert.equal(second.json().data[0].name, maliciousName);
    assert.equal(second.json().pagination.has_more, false);
    assert.equal((await app.inject({ url: '/cameras?active=false&aviary_id=1', headers })).json().data[0].id, 2);
    assert.equal((await app.inject({ url: '/cameras?limit=101', headers })).statusCode, 422);
    assert.equal((await app.inject({ url: '/cameras?active=nao', headers })).statusCode, 422);
    assert.equal((await app.inject({ url: '/cameras?senha=extra', headers })).statusCode, 422);
  });

  it('limita alteracoes conforme o papel verificado do usuario', async () => {
    const { app } = context;
    const operator = { authorization: 'Bearer jwt-operador' };
    assert.equal((await app.inject({ url: '/lots', headers: operator })).statusCode, 200);
    assert.equal((await app.inject({ method: 'POST', url: '/lots', headers: operator,
      payload: { name: 'Nao autorizado' } })).statusCode, 403);
    assert.equal((await app.inject({ method: 'POST', url: '/raspberries', headers: operator,
      payload: { name: 'Dispositivo', hostname: 'operador' } })).statusCode, 201);
  });

  it('recebe analises, persiste niveis e permite consulta com filtros', async () => {
    const { app } = context;
    await chain(app);
    const item = analysis();
    const response = await app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders,
      payload: { schema_version: 1, analyses: [item] } });
    assert.equal(response.statusCode, 200);
    assert.deepEqual(response.json(), { accepted_analysis_ids: [item.analise_id], rejected: [] });
    const detail = (await app.inject({ url: `/analyses/${item.analise_id}`, headers })).json();
    assert.equal(detail.lot_id, 1);
    assert.equal(detail.visible_birds, 23);
    assert.deepEqual(detail.levels.map((level: { percent: number }) => Number(level.percent)), [60, 40]);
    assert.equal(detail.payload.zonas_versao, 'v1');
    const query = '/analyses?camera_id=1&lot_id=1&from=2026-11-12T13%3A00%3A00Z&to=2026-11-12T14%3A00%3A00Z';
    assert.equal((await app.inject({ url: query, headers })).json().data.length, 1);
    assert.equal((await app.inject({ url: '/analyses?camera_id=2', headers })).json().data.length, 0);
    assert.equal((await app.inject({ url: '/analyses?to=2026-11-12T13%3A00%3A00Z', headers })).json().data.length, 0);
  });

  it('reenvio nao duplica e conflito de conteudo nao sobrescreve o resultado', async () => {
    const { app, db } = context;
    await chain(app);
    const item = analysis();
    const send = (value: unknown) => app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders,
      payload: { schema_version: 1, analyses: [value] } });
    await send(item);
    assert.deepEqual((await send(item)).json().accepted_analysis_ids, [item.analise_id]);
    const conflict = await send({ ...item, modelo_versao: 'outra-versao' });
    assert.equal(conflict.json().rejected[0].reason, 'analise_id_conflitante');
    assert.equal((await db.query('SELECT count(*)::int AS count FROM public.analysis')).rows[0].count, 1);
    assert.equal((await db.query('SELECT count(*)::int AS count FROM public.analysis_level_count')).rows[0].count, 2);
  });

  it('recusa cameras/dispositivos inativos e confirma reenvios ja persistidos', async () => {
    const { app } = context;
    await chain(app);
    const item = analysis();
    const send = (value: unknown) => app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders,
      payload: { schema_version: 1, analyses: [value] } });
    await send(item);
    await app.inject({ method: 'PATCH', url: '/cameras/1', headers, payload: { active: false } });
    assert.deepEqual((await send(item)).json().accepted_analysis_ids, [item.analise_id]);
    const next = analysis('22222222-2222-4222-8222-222222222222');
    assert.equal((await send(next)).json().rejected[0].reason, 'camera_inativa');
    await app.inject({ method: 'PATCH', url: '/cameras/1', headers, payload: { active: true } });
    await app.inject({ method: 'PATCH', url: '/raspberries/1', headers, payload: { active: false } });
    assert.equal((await send(next)).json().rejected[0].reason, 'dispositivo_inativo');
  });

  it('isola itens invalidos sem perder os validos e rejeita camera inexistente', async () => {
    const { app } = context;
    await chain(app);
    const valid = analysis();
    const inconsistent = { ...analysis('22222222-2222-4222-8222-222222222222'), total_atribuido_quadro: 999 };
    const unknown = analysis('33333333-3333-4333-8333-333333333333', '999');
    const response = await app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders,
      payload: { schema_version: 1, analyses: [null, inconsistent, valid, unknown] } });
    assert.deepEqual(response.json().accepted_analysis_ids, [valid.analise_id]);
    assert.deepEqual(response.json().rejected.map((item: { reason: string }) => item.reason),
      ['item_invalido', 'item_invalido', 'camera_nao_cadastrada']);
  });

  it('distingue zero valido de imagem inadequada e exige percentuais coerentes', async () => {
    const { app } = context;
    await chain(app);
    const empty = { ...analysis(), quantidade_aves_visiveis: 0, total_atribuido_quadro: 0,
      quantidade_sem_nivel: 0, contagens_por_nivel: { N0: 0, N1: 0 }, percentuais_por_nivel: { N0: null, N1: null } };
    const invalid = { ...analysis('22222222-2222-4222-8222-222222222222'), status: 'imagem_inadequada',
      motivo_status: 'Imagem desfocada', quantidade_aves_visiveis: null, total_atribuido_quadro: null,
      quantidade_sem_nivel: null, contagens_por_nivel: { N0: null, N1: null }, percentuais_por_nivel: { N0: null, N1: null } };
    const wrong = { ...analysis('33333333-3333-4333-8333-333333333333'), percentuais_por_nivel: { N0: 40, N1: 60 } };
    const response = await app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders,
      payload: { schema_version: 1, analyses: [empty, invalid, wrong] } });
    assert.deepEqual(response.json().accepted_analysis_ids, [empty.analise_id, invalid.analise_id]);
    assert.equal(response.json().rejected.length, 1);
    const result = await app.inject({ url: '/analyses?status=imagem_inadequada', headers });
    assert.equal(result.json().data[0].visible_birds, null);
  });

  it('limita o lote, exige JSON valido e nao aceita datas sem fuso', async () => {
    const { app } = context;
    for (const payload of [{ schema_version: 2, analyses: [] }, { schema_version: 1, analyses: Array(501).fill({}) }]) {
      assert.equal((await app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders, payload })).statusCode, 422);
    }
    assert.equal((await app.inject({ method: 'POST', url: '/ingest-analyses',
      headers: { ...syncHeaders, 'content-type': 'application/json' }, payload: '{quebrado' })).statusCode, 400);
    assert.equal((await app.inject({ url: '/analyses?from=2026-11-12T10:00:00', headers })).statusCode, 422);
    assert.equal((await app.inject({ url: '/analyses?from=2026-11-13T00:00:00Z&to=2026-11-12T00:00:00Z', headers })).statusCode, 422);
  });
});

it('falha de conexao vira 503 sem vazar detalhes do banco', async () => {
  let closed = false;
  const db: Database = {
    query: async () => { throw new Error('Senha secreta e URL privada do banco'); },
    transaction: async () => { throw new Error('Nao utilizado'); },
    close: async () => { closed = true; },
  };
  const app = buildApp({ db, apiToken, syncToken });
  const response = await app.inject({ url: '/ready', headers });
  assert.equal(response.statusCode, 503);
  assert.ok(!response.body.includes('Senha'));
  await app.close();
  assert.equal(closed, true);
});
