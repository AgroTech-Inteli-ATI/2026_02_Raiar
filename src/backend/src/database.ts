import { Pool, types, type PoolClient } from 'pg';

// Datas civis nao devem ser convertidas para o fuso do processo Node.
types.setTypeParser(1082, (value: string) => value);

export interface QueryResult {
  rows: Record<string, unknown>[];
}

export interface Database {
  query(text: string, values?: unknown[]): Promise<QueryResult>;
  transaction<T>(work: (connection: Database) => Promise<T>): Promise<T>;
  close(): Promise<void>;
}

function clientDatabase(client: PoolClient): Database {
  return {
    query: (text, values) => client.query(text, values),
    transaction: () => Promise.reject(new Error('Transacao aninhada nao suportada.')),
    close: async () => {},
  };
}

export function createDatabase(connectionString: string, ssl: boolean): Database {
  const url = new URL(connectionString);
  if (['sslmode', 'sslcert', 'sslkey', 'sslrootcert'].some((key) => url.searchParams.has(key))) {
    throw new Error('Configure TLS com DATABASE_SSL e remova parametros SSL de DATABASE_URL.');
  }
  const pool = new Pool({
    connectionString,
    ssl: ssl ? { rejectUnauthorized: true } : false,
    max: 10,
    connectionTimeoutMillis: 5000,
    idleTimeoutMillis: 30000,
    statement_timeout: 15000,
    application_name: 'raiar-backend',
  });
  return databaseFromPool(pool);
}

export function databaseFromPool(pool: Pool): Database {
  pool.on('error', () => console.error('Conexao ociosa com o PostgreSQL indisponivel.'));
  return {
    query: (text, values) => pool.query(text, values),
    async transaction(work) {
      const client = await pool.connect();
      let broken = false;
      try {
        await client.query('BEGIN');
        const result = await work(clientDatabase(client));
        await client.query('COMMIT');
        return result;
      } catch (error) {
        try { await client.query('ROLLBACK'); } catch { broken = true; }
        throw error;
      } finally {
        client.release(broken);
      }
    },
    close: () => pool.end(),
  };
}
