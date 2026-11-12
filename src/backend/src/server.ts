import { buildApp } from './app.js';
import { loadConfig } from './config.js';
import { createDatabase } from './database.js';
import { supabaseUserVerifier } from './auth.js';

async function start() {
  const config = loadConfig();
  const db = createDatabase(config.DATABASE_URL, config.DATABASE_SSL);
  const app = buildApp({
    db, apiToken: config.RAIAR_API_TOKEN, syncToken: config.RAIAR_SYNC_TOKEN, logger: true,
    verifyUser: config.SUPABASE_URL && config.SUPABASE_PUBLISHABLE_KEY
      ? supabaseUserVerifier(config.SUPABASE_URL, config.SUPABASE_PUBLISHABLE_KEY) : undefined,
  });
  try {
    await db.query(`SELECT c.active, c.name, r.active, a.timezone, l.age_days_reference,
      l.age_reference_date, l.age_reference_source, l.archived_at
      FROM public.camera c JOIN public.raspberry r ON r.id = c.raspberry_id
      JOIN public.aviary a ON a.id = c.aviary_id LEFT JOIN public.lot l ON l.id = a.current_lot_id LIMIT 0`);
    await app.listen({ port: config.PORT, host: config.HOST });
  } catch {
    await app.close();
    throw new Error('Falha ao iniciar o backend. Confira conexao e execute npm run migrate.');
  }
  for (const signal of ['SIGINT', 'SIGTERM'] as const) {
    process.once(signal, () => { void app.close().catch(() => { process.exitCode = 1; }); });
  }
}

start().catch((error: Error) => {
  console.error(error.message);
  process.exitCode = 1;
});
