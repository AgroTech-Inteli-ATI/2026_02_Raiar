import { PGlite } from '@electric-sql/pglite';
import type { Database, QueryResult } from '../src/database.js';
import { migrate } from '../src/migrate.js';
import { buildApp } from '../src/app.js';

type Engine = Pick<PGlite, 'query' | 'exec'>;
function connection(engine: Engine): Database {
  return {
    async query(text, values) {
      if (values) return engine.query(text, values) as Promise<QueryResult>;
      const results = await engine.exec(text);
      return { rows: results.at(-1)?.rows as Record<string, unknown>[] ?? [] };
    },
    transaction: () => Promise.reject(new Error('Transacao aninhada nao suportada.')),
    close: async () => {},
  };
}

export function testDatabase() {
  const engine = new PGlite({ parsers: { 1082: (value: string) => value } });
  const db: Database = {
    ...connection(engine),
    transaction: (work) => engine.transaction((tx) => work(connection(tx))),
    close: () => engine.close(),
  };
  return db;
}

export const apiToken = 'api-token-exclusivo-com-mais-de-32-caracteres';
export const syncToken = 'sync-token-exclusivo-com-mais-de-32-caracteres';
export const headers = { authorization: `Bearer ${apiToken}` };
export const syncHeaders = { authorization: `Bearer ${syncToken}` };

export async function setup() {
  const db = testDatabase();
  await migrate(db);
  const app = buildApp({ db, apiToken, syncToken, verifyUser: async (token) =>
    token === 'jwt-operador' ? { subject: 'usuario-operador', role: 'operador' } : null });
  await app.ready();
  return { app, db };
}

export type App = Awaited<ReturnType<typeof setup>>['app'];
export async function chain(app: App) {
  const raspberry = await app.inject({ method: 'POST', url: '/raspberries', headers,
    payload: { name: 'Raspberry 1', hostname: 'raiar-1' } });
  const lot = await app.inject({ method: 'POST', url: '/lots', headers,
    payload: { name: 'Lote 1', age_days_reference: 10, age_reference_date: '2026-11-01', age_reference_source: 'Raiar' } });
  const aviary = await app.inject({ method: 'POST', url: '/aviaries', headers,
    payload: { name: 'Aviario 1', number: 1, type: 'rearing', current_lot_id: lot.json().id } });
  const camera = await app.inject({ method: 'POST', url: '/cameras', headers,
    payload: { name: 'Camera norte', raspberry_id: raspberry.json().id, aviary_id: aviary.json().id } });
  for (const response of [raspberry, lot, aviary, camera]) {
    if (response.statusCode !== 201) throw new Error(response.body);
  }
  return { raspberry: raspberry.json(), lot: lot.json(), aviary: aviary.json(), camera: camera.json() };
}

export function analysis(id = '11111111-1111-4111-8111-111111111111', camera = '1') {
  return {
    analise_id: id, camera_id: camera, quadro_id: 'quadro-1',
    capturado_em: '2026-11-12T10:00:00-03:00', processado_em: '2026-11-12T13:00:02Z',
    status: 'valido', motivo_status: null, quantidade_aves_visiveis: 23,
    total_atribuido_quadro: 20, quantidade_sem_nivel: 3, modelo_versao: 'modelo-teste',
    contagens_por_nivel: { N0: 12, N1: 8 }, percentuais_por_nivel: { N0: 60, N1: 40 },
    zonas_versao: 'v1', config_sha256: 'hash-de-configuracao',
  };
}
