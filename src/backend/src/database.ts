import { Pool, types, type PoolClient, type PoolConfig } from 'pg';

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

export function databasePoolConfig(connectionString: string, ssl: boolean): PoolConfig {
  const url = new URL(connectionString);
  if ([...url.searchParams.keys()].some((key) => ['host', 'hostaddr'].includes(key.toLowerCase()))) {
    throw new Error('Informe o host somente na autoridade de DATABASE_URL.');
  }
  if (!ssl && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
    throw new Error('TLS obrigatorio para banco remoto.');
  }
  // pg interpreta a URL depois das opcoes do pool. Remover todos os parametros TLS
  // impede que ssl=0, ssl=no-verify ou aliases substituam DATABASE_SSL.
  for (const key of [...url.searchParams.keys()]) {
    if (key.toLowerCase().startsWith('ssl') || key.toLowerCase() === 'uselibpqcompat') {
      url.searchParams.delete(key);
    }
  }
  return {
    connectionString: url.toString(),
    ssl: ssl ? { rejectUnauthorized: true } : false,
    max: 10,
    connectionTimeoutMillis: 5000,
    idleTimeoutMillis: 30000,
    statement_timeout: 15000,
    application_name: 'raiar-backend',
  };
}

export function createDatabase(connectionString: string, ssl: boolean): Database {
  return databaseFromPool(new Pool(databasePoolConfig(connectionString, ssl)));
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
