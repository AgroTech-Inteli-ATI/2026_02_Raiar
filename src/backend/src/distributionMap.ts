/**
 * Cálculo isolado para uma futura visualização esquemática por câmera.
 * Os limites precisam ser fornecidos por quem integrar o módulo e são provisórios
 * até validação operacional com a Raiar. Este módulo não registra uma rota.
 */
export type ConcentrationBand = 'baixa' | 'média' | 'alta';

export type ProvisionalConcentrationThresholds = {
  /** Média máxima de aves visíveis por análise classificada como baixa. */
  lowMax: number;
  /** Média máxima de aves visíveis por análise classificada como média. */
  mediumMax: number;
};

export type CameraAnalysisSample = {
  camera_id: number;
  status: string;
  visible_birds: number | null;
  captured_at: string | null;
  processed_at: string;
};

export type CameraDistributionSummary = {
  camera_id: number;
  average_visible_birds: number;
  valid_analysis_count: number;
  last_analysis_at: string;
  concentration: ConcentrationBand;
};

export type DistributionMapOptions = {
  db: Database;
  thresholds?: ProvisionalConcentrationThresholds;
};

const querySchema = z.strictObject({
  camera_id: z.coerce.number().int().positive().optional(),
  aviary_id: z.coerce.number().int().positive().optional(),
  from: z.iso.datetime({ offset: true }).optional(),
  to: z.iso.datetime({ offset: true }).optional(),
  limit: z.coerce.number().int().min(1).max(100).default(50),
  offset: z.coerce.number().int().min(0).max(1000000).default(0),
}).refine((query) => !query.from || !query.to || Date.parse(query.from) <= Date.parse(query.to),
  'O início deve anteceder o fim.');

function validateThresholds(thresholds: ProvisionalConcentrationThresholds) {
  if (!Number.isFinite(thresholds.lowMax) || thresholds.lowMax < 0
    || !Number.isFinite(thresholds.mediumMax) || thresholds.mediumMax < thresholds.lowMax) {
    throw new RangeError('Os limites provisórios devem ser finitos, não negativos e crescentes.');
  }
}

export function classifyConcentration(
  value: number,
  thresholds: ProvisionalConcentrationThresholds,
): ConcentrationBand {
  validateThresholds(thresholds);
  if (value <= thresholds.lowMax) return 'baixa';
  if (value <= thresholds.mediumMax) return 'média';
  return 'alta';
}

/** Lê limites temporários de ambiente. Sem ambos, a rota responde não configurada. */
export function readProvisionalThresholds(
  environment: NodeJS.ProcessEnv = process.env,
): ProvisionalConcentrationThresholds | undefined {
  const low = environment.RAIAR_CONCENTRATION_LOW_MAX;
  const medium = environment.RAIAR_CONCENTRATION_MEDIUM_MAX;
  if (low === undefined && medium === undefined) return undefined;
  if (low === undefined || medium === undefined) {
    throw new Error('Configure juntos RAIAR_CONCENTRATION_LOW_MAX e RAIAR_CONCENTRATION_MEDIUM_MAX.');
  }
  const thresholds = { lowMax: Number(low), mediumMax: Number(medium) };
  validateThresholds(thresholds);
  return thresholds;
}

/** Plugin isolado; o app deve registrá-lo dentro do hook global de autenticação. */
export const distributionMapRoutes: FastifyPluginAsync<DistributionMapOptions> = async (app, options) => {
  app.get('/cameras', async (request, reply) => {
    if (!options.thresholds) {
      return reply.code(503).send({
        error: {
          code: 'distribution_not_configured',
          message: 'Os limites provisórios de concentração ainda não foram configurados.',
        },
      });
    }
    const { camera_id, aviary_id, from, to, limit, offset } = querySchema.parse(request.query);
    const conditions = ["a.status = 'valido'", 'a.visible_birds IS NOT NULL'];
    const values: unknown[] = [];
    for (const [field, value] of [['camera_id', camera_id], ['aviary_id', aviary_id]] as const) {
      if (value !== undefined) {
        values.push(value);
        conditions.push(`a.${field} = $${values.length}`);
      }
    }
    for (const [operator, value] of [['>=', from], ['<', to]] as const) {
      if (value) {
        values.push(value);
        conditions.push(`a.captured_at ${operator} $${values.length}`);
      }
    }
    values.push(limit + 1, offset);
    const { rows } = await options.db.query(`SELECT a.camera_id,
      AVG(a.visible_birds)::double precision AS average_visible_birds,
      COUNT(*)::integer AS valid_analysis_count,
      MAX(COALESCE(a.captured_at, a.processed_at)) AS last_analysis_at
      FROM public.analysis a WHERE ${conditions.join(' AND ')}
      GROUP BY a.camera_id ORDER BY a.camera_id
      LIMIT $${values.length - 1} OFFSET $${values.length}`, values);
    const page = rows.slice(0, limit);
    return {
      data: page.map((row) => {
        const average = Number(row.average_visible_birds);
        return {
          camera_id: Number(row.camera_id),
          average_visible_birds: average,
          valid_analysis_count: Number(row.valid_analysis_count),
          last_analysis_at: new Date(row.last_analysis_at as string | Date).toISOString(),
          concentration: classifyConcentration(average, options.thresholds!),
        };
      }),
      pagination: { limit, offset, has_more: rows.length > limit },
    };
  });
};

/**
 * Calcula a média de aves visíveis por análise válida de cada câmera.
 * A janela temporal deve ser aplicada pelo chamador antes de invocar esta função.
 * Análises inválidas ou sem contagem/timestamp utilizável são ignoradas.
 */
export function summarizeCameraDistribution(
  analyses: readonly CameraAnalysisSample[],
  thresholds: ProvisionalConcentrationThresholds,
): CameraDistributionSummary[] {
  validateThresholds(thresholds);

  const grouped = new Map<number, { total: number; count: number; latestTimestamp: number; latestAt: string }>();
  for (const analysis of analyses) {
    if (analysis.status !== 'valido' || analysis.visible_birds === null
      || !Number.isInteger(analysis.visible_birds) || analysis.visible_birds < 0
      || !Number.isInteger(analysis.camera_id) || analysis.camera_id <= 0) continue;

    const timestamp = analysis.captured_at ?? analysis.processed_at;
    const parsedTimestamp = Date.parse(timestamp);
    if (!Number.isFinite(parsedTimestamp)) continue;

    const current = grouped.get(analysis.camera_id) ?? {
      total: 0,
      count: 0,
      latestTimestamp: Number.NEGATIVE_INFINITY,
      latestAt: '',
    };
    current.total += analysis.visible_birds;
    current.count += 1;
    if (parsedTimestamp > current.latestTimestamp) {
      current.latestTimestamp = parsedTimestamp;
      current.latestAt = new Date(parsedTimestamp).toISOString();
    }
    grouped.set(analysis.camera_id, current);
  }

  return [...grouped.entries()]
    .map(([cameraId, summary]) => {
      const average = summary.total / summary.count;
      return {
        camera_id: cameraId,
        average_visible_birds: average,
        valid_analysis_count: summary.count,
        last_analysis_at: summary.latestAt,
        concentration: classifyConcentration(average, thresholds),
      };
    })
    .sort((first, second) => first.camera_id - second.camera_id);
}
import type { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import type { Database } from './database.js';
