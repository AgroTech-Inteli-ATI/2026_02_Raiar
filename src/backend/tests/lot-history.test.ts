import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { after, before, beforeEach, describe, it } from 'node:test';
import { setup, chain, analysis, headers, syncHeaders } from './helpers.js';

describe('Historico de ocupacao e lote na captura', { concurrency: false }, () => {
  let context: Awaited<ReturnType<typeof setup>>;
  before(async () => { context = await setup(); });
  after(async () => { await context?.app.close(); });
  beforeEach(async () => {
    await context.db.query(`TRUNCATE public.analysis_level_count, public.analysis, public.alerts,
      public.aviary_lot_assignment, public.camera, public.aviary, public.lot,
      public.raspberry RESTART IDENTITY CASCADE`);
    await chain(context.app);
    const created = await context.app.inject({ method: 'POST', url: '/lots', headers, payload: { name: 'Lote 2' } });
    assert.equal(created.statusCode, 201);
  });

  const assign = (lot: number | null, at: string, aviary = 1) => context.app.inject({
    method: 'POST', url: `/aviaries/${aviary}/lot-assignments`, headers,
    payload: { lot_id: lot, effective_at: at },
  });
  const history = async () => (await context.app.inject({ url: '/aviaries/1/lot-assignments', headers })).json().data;
  const send = (items: unknown[]) => context.app.inject({ method: 'POST', url: '/ingest-analyses', headers: syncHeaders,
    payload: { schema_version: 1, analyses: items } });
  const frameAt = (captured: string | null) => ({ ...analysis(randomUUID()), capturado_em: captured });
  const detail = async (id: string) => (await context.app.inject({ url: `/analyses/${id}`, headers })).json();

  it('recebe imagens antigas depois da troca sem associa-las ao lote novo', async () => {
    const boundary = '2026-11-12T13:00:00Z';
    assert.equal((await assign(2, boundary)).statusCode, 200);
    const periods = await history();
    assert.equal(periods.length, 2);
    assert.equal(periods[0].lot_id, 1);
    assert.equal(new Date(periods[0].ended_at).toISOString(), new Date(boundary).toISOString());
    assert.equal(periods[1].lot_id, 2);
    assert.equal(periods[1].ended_at, null);

    const old = frameAt('2026-11-12T09:59:59.999-03:00');
    const exact = frameAt('2026-11-12T10:00:00-03:00');
    const recent = frameAt('2026-11-12T14:00:00Z');
    const received = await send([recent, old, exact]);
    assert.deepEqual(received.json().accepted_analysis_ids, [recent.analise_id, old.analise_id, exact.analise_id]);
    assert.deepEqual(received.json().rejected, []);
    for (const [item, lot, period] of [[old, 1, periods[0]], [exact, 2, periods[1]], [recent, 2, periods[1]]] as const) {
      const saved = await detail(item.analise_id);
      assert.equal(saved.lot_id, lot);
      assert.equal(saved.lot_assignment_id, period.id);
      assert.equal(saved.lot_association_status, 'matched');
      assert.equal(saved.levels.length, 2);
    }
    assert.equal((await context.app.inject({ url: '/analyses?lot_id=1', headers })).json().data.length, 1);
    assert.equal((await context.app.inject({ url: '/analyses?lot_id=2', headers })).json().data.length, 2);
    assert.equal((await context.app.inject({ url: '/aviaries/1', headers })).json().current_lot_id, 2);

    await assign(null, '2026-11-13T00:00:00Z');
    assert.deepEqual((await send([old, recent])).json().accepted_analysis_ids, [old.analise_id, recent.analise_id]);
    assert.equal((await detail(old.analise_id)).lot_id, 1);
    assert.equal((await detail(recent.analise_id)).lot_id, 2);
    assert.equal((await history()).length, 2);
  });

  it('preserva o aviario de capturas pendentes e exige novo ID ao mover a camera fisica', async () => {
    const other = await context.app.inject({ method: 'POST', url: '/aviaries', headers,
      payload: { name: 'Outro aviario', number: 2, type: 'normal' } });
    const otherId = other.json().id;
    assert.equal(other.statusCode, 201);
    assert.equal((await assign(2, '2026-11-01T00:00:00Z', otherId)).statusCode, 200);
    // A captura ainda esta somente na fila do no: nao ha analises persistidas.
    const old = frameAt('2026-11-12T12:00:00Z');
    const move = await context.app.inject({ method: 'PATCH', url: '/cameras/1', headers,
      payload: { aviary_id: otherId, name: 'Camera movida' } });
    assert.equal(move.statusCode, 422);
    await assert.rejects(context.db.query('UPDATE public.camera SET aviary_id = $1 WHERE id = 1', [otherId]),
      (error: unknown) => (error as { code: string }).code === '23514');
    const unchanged = await context.app.inject({ method: 'PATCH', url: '/cameras/1', headers,
      payload: { aviary_id: 1, name: 'Camera original' } });
    assert.equal(unchanged.statusCode, 200);
    assert.equal(unchanged.json().aviary_id, 1);

    const newCamera = await context.app.inject({ method: 'POST', url: '/cameras', headers,
      payload: { raspberry_id: 1, aviary_id: otherId, name: 'Camera movida' } });
    assert.equal(newCamera.statusCode, 201);
    const recent = { ...frameAt('2026-11-13T12:00:00Z'), camera_id: String(newCamera.json().id) };
    assert.deepEqual((await send([recent, old])).json().accepted_analysis_ids,
      [recent.analise_id, old.analise_id]);
    for (const [item, aviary, lot] of [[old, 1, 1], [recent, otherId, 2]] as const) {
      const saved = await detail(item.analise_id);
      assert.equal(saved.aviary_id, aviary);
      assert.equal(saved.lot_id, lot);
      assert.equal(saved.lot_association_status, 'matched');
    }
  });

  it('mantem lacunas e horario desconhecido explicitos, sem usar o lote atual como fallback', async () => {
    await assign(null, '2026-11-05T00:00:00Z');
    await assign(2, '2026-11-07T00:00:00Z');
    const before = frameAt('2026-10-31T23:59:59Z');
    const gap = frameAt('2026-11-06T12:00:00Z');
    const missing = frameAt(null);
    const received = await send([before, gap, missing]);
    assert.equal(received.json().accepted_analysis_ids.length, 3);
    for (const item of [before, gap, missing]) {
      const saved = await detail(item.analise_id);
      assert.equal(saved.lot_id, null);
      assert.equal(saved.lot_assignment_id, null);
      assert.equal(saved.lot_association_status, item === missing ? 'no_capture_time' : 'no_occupancy');
    }
    const closedAt = frameAt('2026-11-05T00:00:00Z');
    await send([closedAt]);
    assert.equal((await detail(closedAt.analise_id)).lot_association_status, 'no_occupancy');
    assert.equal((await context.app.inject({ url: '/analyses?lot_association_status=no_occupancy', headers }))
      .json().data.length, 3);
  });

  it('confere o lote informado pelo no e aplica a regra tambem no RPC SQL da Edge Function', async () => {
    await assign(2, '2026-11-12T13:00:00Z');
    const old = { ...frameAt('2026-11-12T12:00:00Z'), lote_id: '1' };
    const wrong = { ...frameAt('2026-11-12T12:00:00Z'), lote_id: '2' };
    const naive = frameAt('2026-11-12T12:00:00');
    const result = await context.db.query('SELECT public.ingest_analyses($1::jsonb) AS result',
      [JSON.stringify({ schema_version: 1, analyses: [old, wrong, naive] })]);
    assert.deepEqual(result.rows[0].result, {
      accepted_analysis_ids: [old.analise_id],
      rejected: [{ id: wrong.analise_id, reason: 'lote_divergente' },
        { id: naive.analise_id, reason: 'capturado_em_invalido' }],
    });
    assert.equal((await detail(old.analise_id)).lot_id, 1);
    assert.equal((await send([wrong])).json().rejected[0].reason, 'lote_divergente');
  });

  it('impede sobreposicoes por aviario e por lote no proprio banco', async () => {
    await assert.rejects(context.db.query(`INSERT INTO public.aviary_lot_assignment
      (aviary_id, lot_id, started_at, ended_at) VALUES (1, 2, '2026-11-02T00:00:00Z', '2026-11-03T00:00:00Z')`),
    (error: unknown) => (error as { code: string }).code === '23P01');
    const other = await context.app.inject({ method: 'POST', url: '/aviaries', headers,
      payload: { name: 'Outro aviario', number: 2, type: 'rearing' } });
    assert.equal(other.statusCode, 201);
    await assert.rejects(context.db.query(`INSERT INTO public.aviary_lot_assignment
      (aviary_id, lot_id, started_at) VALUES ($1, 1, '2026-11-02T00:00:00Z')`, [other.json().id]),
    (error: unknown) => (error as { code: string }).code === '23P01');
    assert.equal((await history()).length, 1);
  });

  it('uma troca invalida reverte tanto o cadastro atual quanto o historico', async () => {
    assert.equal((await assign(2, '2026-10-31T00:00:00Z')).statusCode, 422);
    assert.equal((await assign(2, '2026-11-01T00:00:00Z')).statusCode, 422);
    assert.equal((await assign(999, '2026-11-12T13:00:00Z')).statusCode, 409);
    assert.equal((await history()).length, 1);
    assert.equal((await context.app.inject({ url: '/aviaries/1', headers })).json().current_lot_id, 1);
    // PATCH compativel com clientes antigos registra a troca automaticamente no instante atual.
    const response = await context.app.inject({ method: 'PATCH', url: '/aviaries/1', headers,
      payload: { current_lot_id: 2 } });
    assert.equal(response.statusCode, 200);
    const periods = await history();
    assert.equal(periods.length, 2);
    assert.ok(Math.abs(Date.now() - Date.parse(periods[1].started_at)) < 10000);
    assert.equal(periods[0].ended_at, periods[1].started_at);
  });

  it('trocas repetidas sao idempotentes e configuracao temporal nao vaza para outras operacoes', async () => {
    await assign(2, '2026-11-12T13:00:00Z');
    await assign(2, '2026-11-12T13:00:00Z');
    const response = await context.app.inject({ method: 'PATCH', url: '/aviaries/1', headers,
      payload: { name: 'Nome atualizado', current_lot_id: 2 } });
    assert.equal(response.statusCode, 200);
    assert.equal((await history()).length, 2);
    assert.equal((await context.db.query("SELECT current_setting('raiar.lot_effective_at', true) AS value")).rows[0].value, '');
  });

  it('nao permite encurtar a ocupacao de uma analise que ja foi associada', async () => {
    const item = frameAt('2026-11-12T13:00:00Z');
    assert.equal((await send([item])).json().accepted_analysis_ids.length, 1);
    assert.equal((await assign(2, '2026-11-12T12:00:00Z')).statusCode, 422);
    const periods = await history();
    assert.equal(periods.length, 1);
    assert.equal(periods[0].ended_at, null);
    assert.equal((await detail(item.analise_id)).lot_id, 1);
  });

  it('protege a alteracao por perfil e recusa datas futuras ou aviarios inexistentes', async () => {
    const response = await context.app.inject({ method: 'POST', url: '/aviaries/1/lot-assignments',
      headers: { authorization: 'Bearer jwt-operador' },
      payload: { lot_id: 2, effective_at: '2026-11-12T13:00:00Z' } });
    assert.equal(response.statusCode, 403);
    assert.equal((await assign(2, '9999-01-01T00:00:00Z')).statusCode, 422);
    assert.equal((await assign(2, '2026-11-12T13:00:00Z', 999)).statusCode, 404);
    assert.equal((await context.app.inject({ url: '/aviaries/999/lot-assignments', headers })).statusCode, 404);
    assert.equal((await context.app.inject({ url: '/aviaries/1/lot-assignments',
      headers: { authorization: 'Bearer jwt-operador' } })).statusCode, 200);
  });
});
