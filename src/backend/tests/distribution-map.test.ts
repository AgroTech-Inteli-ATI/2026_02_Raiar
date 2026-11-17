import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import Fastify from 'fastify';
import {
  distributionMapRoutes,
  readProvisionalThresholds,
  summarizeCameraDistribution,
} from '../src/distributionMap.js';
import type { Database } from '../src/database.js';

const thresholds = { lowMax: 5, mediumMax: 10 };

describe('resumo provisório de distribuição por câmera', () => {
  it('agrupa análises válidas, calcula média e classifica usando limites injetados', () => {
    const result = summarizeCameraDistribution([
      { camera_id: 2, status: 'valido', visible_birds: 4, captured_at: '2026-11-15T10:00:00Z', processed_at: '2026-11-15T10:01:00Z' },
      { camera_id: 1, status: 'valido', visible_birds: 8, captured_at: '2026-11-15T10:00:00Z', processed_at: '2026-11-15T10:01:00Z' },
      { camera_id: 2, status: 'valido', visible_birds: 8, captured_at: '2026-11-15T10:02:00Z', processed_at: '2026-11-15T10:03:00Z' },
      { camera_id: 3, status: 'valido', visible_birds: 12, captured_at: '2026-11-15T10:00:00Z', processed_at: '2026-11-15T10:01:00Z' },
    ], thresholds);

    assert.deepEqual(result.map(({ camera_id, average_visible_birds, concentration }) => ({
      camera_id, average_visible_birds, concentration,
    })), [
      { camera_id: 1, average_visible_birds: 8, concentration: 'média' },
      { camera_id: 2, average_visible_birds: 6, concentration: 'média' },
      { camera_id: 3, average_visible_birds: 12, concentration: 'alta' },
    ]);
    assert.equal(result[1].valid_analysis_count, 2);
    assert.equal(result[1].last_analysis_at, '2026-11-15T10:02:00.000Z');
  });

  it('ignora análises inválidas, sem contagem ou com timestamp inválido', () => {
    const result = summarizeCameraDistribution([
      { camera_id: 1, status: 'imagem_inadequada', visible_birds: null, captured_at: null, processed_at: '2026-11-15T10:00:00Z' },
      { camera_id: 2, status: 'valido', visible_birds: null, captured_at: null, processed_at: '2026-11-15T10:00:00Z' },
      { camera_id: 3, status: 'valido', visible_birds: 2, captured_at: 'data-inválida', processed_at: '2026-11-15T10:00:00Z' },
    ], thresholds);
    assert.deepEqual(result, []);
  });

  it('usa o horário de processamento quando a captura não tem horário', () => {
    const [result] = summarizeCameraDistribution([
      { camera_id: 4, status: 'valido', visible_birds: 0, captured_at: null, processed_at: '2026-11-15T10:00:00-03:00' },
    ], thresholds);
    assert.equal(result.last_analysis_at, '2026-11-15T13:00:00.000Z');
    assert.equal(result.concentration, 'baixa');
  });

  it('rejeita limites não finitos, negativos ou fora de ordem', () => {
    assert.throws(() => summarizeCameraDistribution([], { lowMax: -1, mediumMax: 10 }), RangeError);
    assert.throws(() => summarizeCameraDistribution([], { lowMax: 8, mediumMax: 5 }), RangeError);
    assert.throws(() => summarizeCameraDistribution([], { lowMax: 0, mediumMax: Number.POSITIVE_INFINITY }), RangeError);
  });

  it('lê os limites provisórios da configuração de ambiente', () => {
    assert.deepEqual(readProvisionalThresholds({}), undefined);
    assert.deepEqual(readProvisionalThresholds({
      RAIAR_CONCENTRATION_LOW_MAX: '6',
      RAIAR_CONCENTRATION_MEDIUM_MAX: '12',
    }), { lowMax: 6, mediumMax: 12 });
    assert.throws(() => readProvisionalThresholds({ RAIAR_CONCENTRATION_LOW_MAX: '6' }), /Configure juntos/);
  });

  it('expõe paginação, filtros e classificação através do plugin isolado', async () => {
    let capturedSql = '';
    let capturedValues: unknown[] = [];
    const db: Database = {
      query: async (sql: string, values: unknown[] = []) => {
        capturedSql = sql;
        capturedValues = values;
        return { rows: [{ camera_id: 7, average_visible_birds: 8, valid_analysis_count: 3,
          last_analysis_at: new Date('2026-11-15T10:00:00Z') }] };
      },
      transaction: async <T>(_work: (connection: Database) => Promise<T>): Promise<T> => {
        throw new Error('Transação não esperada.');
      },
      close: async () => {},
    };
    const app = Fastify();
    await app.register(distributionMapRoutes, { db, thresholds });
    try {
      const response = await app.inject({
        url: '/cameras?camera_id=7&aviary_id=2&from=2026-11-01T00%3A00%3A00Z&to=2026-11-16T00%3A00%3A00Z&limit=10&offset=5',
      });
      assert.equal(response.statusCode, 200);
      assert.deepEqual(response.json(), {
        data: [{ camera_id: 7, average_visible_birds: 8, valid_analysis_count: 3,
          last_analysis_at: '2026-11-15T10:00:00.000Z', concentration: 'média' }],
        pagination: { limit: 10, offset: 5, has_more: false },
      });
      assert.match(capturedSql, /GROUP BY a\.camera_id/);
      assert.deepEqual(capturedValues, [7, 2, '2026-11-01T00:00:00Z', '2026-11-16T00:00:00Z', 11, 5]);
    } finally {
      await app.close();
    }
  });

  it('não classifica sem limites configurados', async () => {
    const db: Database = {
      query: async () => { throw new Error('Não deveria consultar.'); },
      transaction: async <T>(_work: (connection: Database) => Promise<T>): Promise<T> => {
        throw new Error('Transação não esperada.');
      },
      close: async () => {},
    };
    const app = Fastify();
    await app.register(distributionMapRoutes, { db });
    try {
      const response = await app.inject('/cameras');
      assert.equal(response.statusCode, 503);
      assert.equal(response.json().error.code, 'distribution_not_configured');
    } finally {
      await app.close();
    }
  });
});
