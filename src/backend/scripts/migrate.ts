import { loadConfig } from '../src/config.js';
import { createDatabase } from '../src/database.js';
import { migrate } from '../src/migrate.js';

async function main() {
  const config = loadConfig();
  const db = createDatabase(config.DATABASE_URL, config.DATABASE_SSL);
  try {
    const applied = await migrate(db);
    console.log(applied.length ? `Migracoes: ${applied.join(', ')}` : 'Banco atualizado.');
  } finally {
    await db.close();
  }
}

main().catch(() => {
  console.error('Migracao falhou. Confira acesso ao banco, integridade das migracoes e esquema existente.');
  process.exitCode = 1;
});
