import 'dotenv/config';
import { z } from 'zod';

const settings = z.object({
  DATABASE_URL: z.url().refine((value) => ['postgres:', 'postgresql:'].includes(new URL(value).protocol)),
  DATABASE_SSL: z.enum(['true', 'false']).default('true').transform((value) => value === 'true'),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  HOST: z.string().min(1).default('127.0.0.1'),
  RAIAR_API_TOKEN: z.string().min(32).refine((value) => !value.startsWith('SUBSTITUA_')),
  RAIAR_SYNC_TOKEN: z.string().min(32).refine((value) => !value.startsWith('SUBSTITUA_')),
  SUPABASE_URL: z.url().optional(),
  SUPABASE_PUBLISHABLE_KEY: z.string().min(1).optional(),
}).superRefine((value, context) => {
  if (value.RAIAR_API_TOKEN === value.RAIAR_SYNC_TOKEN) {
    context.addIssue({ code: 'custom', path: ['RAIAR_SYNC_TOKEN'], message: 'Use segredos distintos.' });
  }
  if (Boolean(value.SUPABASE_URL) !== Boolean(value.SUPABASE_PUBLISHABLE_KEY)) {
    context.addIssue({ code: 'custom', path: ['SUPABASE_URL'], message: 'Configure URL e chave juntas.' });
  }
  if (value.SUPABASE_URL && new URL(value.SUPABASE_URL).protocol !== 'https:') {
    context.addIssue({ code: 'custom', path: ['SUPABASE_URL'], message: 'Use HTTPS.' });
  }
  if (!value.DATABASE_SSL && !['localhost', '127.0.0.1', '[::1]'].includes(new URL(value.DATABASE_URL).hostname)) {
    context.addIssue({ code: 'custom', path: ['DATABASE_SSL'], message: 'TLS obrigatorio para banco remoto.' });
  }
});

export function loadConfig(environment = process.env) {
  const result = settings.safeParse(environment);
  if (!result.success) {
    // Somente os nomes dos campos; os valores podem conter senhas.
    const fields = [...new Set(result.error.issues.map((issue) => issue.path.join('.')))];
    throw new Error(`Configuracao invalida: ${fields.join(', ')}.`);
  }
  return result.data;
}
