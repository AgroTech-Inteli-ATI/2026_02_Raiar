import Fastify from 'fastify';
import { z, ZodError } from 'zod';
import type { Database } from './database.js';
import { ApiError } from './errors.js';
import { tokensEqual, type UserVerifier, type Principal } from './auth.js';
import { resources, pathId, analysisFilter, analysisItem, batchSchema } from './schemas.js';

export interface AppOptions {
  db: Database;
  apiToken: string;
  syncToken: string;
  verifyUser?: UserVerifier;
  logger?: boolean;
}

export function buildApp(options: AppOptions) {
  const { db } = options;
  const app = Fastify({
    logger: options.logger ? { redact: ['req.headers.authorization'] } : false,
    bodyLimit: 5 * 1024 * 1024,
  });
  const identities = new WeakMap<object, Principal>();

  app.setErrorHandler((error, request, reply) => {
    if (error instanceof ZodError) {
      return reply.code(422).send({ error: { code: 'invalid_data', message: 'Dados invalidos.',
        details: error.issues.map((issue) => ({ field: issue.path.join('.'), message: issue.message })) } });
    }
    if (error instanceof ApiError) {
      return reply.code(error.status).send({ error: { code: error.code, message: error.message } });
    }
    const failure = error as { code?: string; statusCode?: number };
    const databaseErrors: Record<string, [number, string, string]> = {
      '23505': [409, 'duplicate_record', 'Registro ou associacao ja existente.'],
      '23503': [409, 'invalid_reference', 'Cadastro relacionado inexistente ou em uso.'],
      '23514': [422, 'invalid_data', 'Dados violam uma regra do cadastro.'],
      '23502': [422, 'invalid_data', 'Campo obrigatorio ausente.'],
      '22007': [422, 'invalid_data', 'Data ou horario invalido.'],
      '22008': [422, 'invalid_data', 'Data ou horario fora do intervalo.'],
    };
    const mapped = databaseErrors[failure.code ?? ''];
    if (mapped) return reply.code(mapped[0]).send({ error: { code: mapped[1], message: mapped[2] } });
    if (failure.statusCode && failure.statusCode < 500) {
      return reply.code(failure.statusCode).send({ error: { code: 'invalid_request', message: 'Requisicao invalida.' } });
    }
    // Nao registrar SQL, payload ou mensagens do driver (podem conter credenciais e dados).
    request.log.error({ failureCode: failure.code ?? 'unknown' }, 'Operacao do backend falhou.');
    return reply.code(503).send({ error: { code: 'service_unavailable', message: 'Servico temporariamente indisponivel.' } });
  });

  app.addHook('onRequest', async (request, reply) => {
    const route = request.routeOptions.url;
    if (route === '/health') return;
    const header = request.headers.authorization ?? '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : '';
    if (!token) return reply.header('WWW-Authenticate', 'Bearer').code(401)
      .send({ error: { code: 'unauthorized', message: 'Autenticacao obrigatoria.' } });
    if (route === '/ingest-analyses') {
      if (!tokensEqual(token, options.syncToken)) throw new ApiError(401, 'unauthorized', 'Credencial invalida.');
      return;
    }
    let principal: Principal | null = null;
    if (tokensEqual(token, options.apiToken)) principal = { subject: 'service', role: 'gestor' };
    else if (options.verifyUser) principal = await options.verifyUser(token);
    if (!principal) throw new ApiError(401, 'unauthorized', 'Credencial invalida.');
    identities.set(request, principal);
  });
  app.addHook('onClose', async () => db.close());

  app.get('/health', async () => ({ status: 'ok' }));
  app.get('/ready', async () => {
    await db.query('SELECT 1');
    return { status: 'ok', database: 'connected' };
  });
  app.get('/me', async (request) => identities.get(request));

  for (const resource of resources) {
    const table = resource.table;
    const shape = resource.schema.shape;
    const columns = ['id', ...Object.keys(shape)];
    const select = columns.join(', ');
    const authorizeWrite = (request: object) => {
      if (!resource.operatorWrite && identities.get(request)?.role !== 'gestor') {
        throw new ApiError(403, 'forbidden', 'Seu perfil nao permite alterar este cadastro.');
      }
    };

    app.get(`/${resource.path}`, async (request) => {
      const { limit, offset, ...filters } = resource.list.parse(request.query);
      const values: unknown[] = [];
      const conditions = Object.entries(filters).map(([field, value]) => {
        if (field === 'archived') return `archived_at IS ${value ? 'NOT ' : ''}NULL`;
        values.push(value);
        return `${field} = $${values.length}`;
      });
      values.push(limit + 1, offset);
      const result = await db.query(`SELECT ${select} FROM public.${table}
        ${conditions.length ? `WHERE ${conditions.join(' AND ')}` : ''}
        ORDER BY id LIMIT $${values.length - 1} OFFSET $${values.length}`, values);
      return { data: result.rows.slice(0, limit), pagination: { limit, offset, has_more: result.rows.length > limit } };
    });

    app.get(`/${resource.path}/:id`, async (request) => {
      const { id } = pathId.parse(request.params);
      const result = await db.query(`SELECT ${select} FROM public.${table} WHERE id = $1`, [id]);
      if (!result.rows[0]) throw new ApiError(404, 'not_found', 'Cadastro nao encontrado.');
      return result.rows[0];
    });

    app.post(`/${resource.path}`, async (request, reply) => {
      authorizeWrite(request);
      const input = resource.schema.parse(request.body) as Record<string, unknown>;
      const fields = Object.keys(input);
      const placeholders = fields.map((_, index) => `$${index + 1}`).join(', ');
      const result = await db.query(`INSERT INTO public.${table} (${fields.join(', ')})
        VALUES (${placeholders}) RETURNING ${select}`, Object.values(input));
      return reply.code(201).header('Location', `/${resource.path}/${result.rows[0].id}`).send(result.rows[0]);
    });

    app.patch(`/${resource.path}/:id`, async (request) => {
      authorizeWrite(request);
      const { id } = pathId.parse(request.params);
      const input = resource.patch.parse(request.body) as Record<string, unknown>;
      const fields = Object.keys(input);
      const assignments = fields.map((field, index) => `${field} = $${index + 1}`).join(', ');
      const values = [...Object.values(input), id];
      const result = await db.query(`UPDATE public.${table} SET ${assignments}
        WHERE id = $${values.length} RETURNING ${select}`, values);
      if (!result.rows[0]) throw new ApiError(404, 'not_found', 'Cadastro nao encontrado.');
      return result.rows[0];
    });
  }

  app.post('/ingest-analyses', async (request) => {
    const batch = batchSchema.parse(request.body);
    const analyses: unknown[] = [];
    const rejected: { id: string | null; reason: string }[] = [];
    for (const item of batch.analyses) {
      const parsed = analysisItem.safeParse(item);
      if (parsed.success) analyses.push(parsed.data);
      else {
        const rawId = item && typeof item === 'object' ? (item as Record<string, unknown>).analise_id : null;
        rejected.push({ id: typeof rawId === 'string' && rawId.length <= 128 ? rawId : null, reason: 'item_invalido' });
      }
    }
    if (!analyses.length) return { accepted_analysis_ids: [], rejected };
    const { rows } = await db.query('SELECT public.ingest_analyses($1::jsonb) AS result',
      [JSON.stringify({ schema_version: 1, analyses })]);
    const result = rows[0].result as { accepted_analysis_ids: string[]; rejected: typeof rejected };
    return { accepted_analysis_ids: result.accepted_analysis_ids, rejected: [...rejected, ...result.rejected] };
  });

  app.get('/analyses', async (request) => {
    const { limit, offset, from, to, ...filters } = analysisFilter.parse(request.query);
    const values: unknown[] = [];
    const conditions = Object.entries(filters).map(([field, value]) => {
      values.push(value);
      return `a.${field} = $${values.length}`;
    });
    for (const [operator, value] of [['>=', from], ['<', to]] as const) {
      if (value) {
        values.push(value);
        conditions.push(`a.captured_at ${operator} $${values.length}`);
      }
    }
    values.push(limit + 1, offset);
    const result = await db.query(`SELECT a.id, a.camera_id, a.aviary_id, a.lot_id, a.frame_id,
      a.captured_at, a.processed_at, a.received_at, a.status, a.status_reason,
      a.visible_birds, a.assigned_total, a.unassigned_birds, a.model_version,
      COALESCE((SELECT jsonb_agg(jsonb_build_object('level_id', l.level_id,
        'bird_count', l.bird_count, 'percent', l.percent) ORDER BY l.level_id)
        FROM public.analysis_level_count l WHERE l.analysis_id = a.id), '[]'::jsonb) AS levels
      FROM public.analysis a ${conditions.length ? `WHERE ${conditions.join(' AND ')}` : ''}
      ORDER BY a.captured_at DESC NULLS LAST, a.processed_at DESC, a.id
      LIMIT $${values.length - 1} OFFSET $${values.length}`, values);
    return { data: result.rows.slice(0, limit), pagination: { limit, offset, has_more: result.rows.length > limit } };
  });

  app.get('/analyses/:id', async (request) => {
    const { id } = z.object({ id: z.uuid() }).parse(request.params);
    const { rows } = await db.query('SELECT * FROM public.analysis WHERE id = $1', [id]);
    if (!rows[0]) throw new ApiError(404, 'not_found', 'Analise nao encontrada.');
    const levels = await db.query(`SELECT level_id, bird_count, percent FROM public.analysis_level_count
      WHERE analysis_id = $1 ORDER BY level_id`, [id]);
    return { ...rows[0], levels: levels.rows };
  });

  return app;
}
