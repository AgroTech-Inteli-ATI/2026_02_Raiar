import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import type { Database } from './database.js';

// O caminho do SQL tambem precisa funcionar no JavaScript compilado em src/backend/dist/src/.
const sqlRoot = fileURLToPath(new URL(import.meta.url.includes('/dist/')
  ? '../../../database/' : '../../database/', import.meta.url));
export const migrationFiles = ['002_analises.sql', '003_dados_cadastro.sql', '004_ingestao_backend.sql'];
export const transactionBody = (sql: string) => sql.replace(/^BEGIN;\s*$/m, '').replace(/^COMMIT;\s*$/m, '');

export async function migrate(db: Database, root = sqlRoot) {
  const applied: string[] = [];
  await db.transaction(async (connection) => {
    await connection.query('SELECT pg_advisory_xact_lock(72424401)');
    await connection.query(`CREATE SCHEMA IF NOT EXISTS backend_internal`);
    await connection.query(`CREATE TABLE IF NOT EXISTS backend_internal.migration (
      name text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())`);
    const { rows: tables } = await connection.query(`SELECT table_name FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name IN ('raspberry', 'lot', 'aviary', 'camera', 'alerts')`);
    if (!tables.length) {
      await connection.query(transactionBody(await readFile(resolve(root, 'schema.sql'), 'utf8')));
      applied.push('schema.sql');
    } else if (tables.length !== 5) {
      throw new Error('Esquema inicial incompleto; revise o banco antes de migrar.');
    }
    for (const name of migrationFiles) {
      const sql = await readFile(resolve(root, 'migrations', name), 'utf8');
      const checksum = createHash('sha256').update(sql).digest('hex');
      const previous = await connection.query('SELECT checksum FROM backend_internal.migration WHERE name = $1', [name]);
      if (previous.rows[0]) {
        if (previous.rows[0].checksum !== checksum) throw new Error(`Migracao aplicada foi alterada: ${name}.`);
        continue;
      }
      let adopted = false;
      if (name === '002_analises.sql') {
        const existing = await connection.query(`SELECT to_regclass('public.analysis') IS NOT NULL AS analysis,
          to_regclass('public.analysis_level_count') IS NOT NULL AS levels,
          to_regprocedure('public.ingest_analyses(jsonb)') IS NOT NULL AS ingest`);
        const values = Object.values(existing.rows[0]);
        adopted = values.every(Boolean);
        if (!adopted && values.some(Boolean)) throw new Error('Migracao 002 parcialmente aplicada; revise o banco.');
      }
      if (!adopted) await connection.query(transactionBody(sql));
      await connection.query('INSERT INTO backend_internal.migration (name, checksum) VALUES ($1, $2)', [name, checksum]);
      applied.push(adopted ? `${name} (existente)` : name);
    }
  });
  return applied;
}
