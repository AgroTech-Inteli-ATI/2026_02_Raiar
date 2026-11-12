import { z } from 'zod';

const text = z.string().trim().min(1).max(255);
const id = z.number().int().positive().max(2147483647);
const queryId = z.coerce.number().int().positive().max(2147483647);
const booleanQuery = z.enum(['true', 'false']).transform((value) => value === 'true');
const instant = z.iso.datetime({ offset: true });
const date = z.iso.date();

const raspberry = z.strictObject({
  name: text, hostname: text, model: text.nullable().optional(), active: z.boolean().optional(),
});
const lot = z.strictObject({
  name: text,
  age_days_reference: z.number().int().nonnegative().max(2147483647).nullable().optional(),
  age_reference_date: date.nullable().optional(),
  age_reference_source: z.string().trim().min(1).max(2000).nullable().optional(),
  archived_at: instant.nullable().optional(),
});
const aviary = z.strictObject({
  name: text, number: z.number().int().positive().max(2147483647),
  box_identifiers: z.array(text).max(1000).refine((boxes) => new Set(boxes).size === boxes.length,
    'Boxes repetidos.').nullable().optional(),
  type: z.enum(['rearing', 'normal']), registration_date: date.optional(),
  timezone: text.optional(), current_lot_id: id.nullable().optional(),
});
const camera = z.strictObject({
  name: text.nullable().optional(), raspberry_id: id, model: text.nullable().optional(),
  aviary_id: id, active: z.boolean().optional(),
});

const notEmpty = (value: Record<string, unknown>) => Object.keys(value).length > 0;
const ageComplete = (value: Record<string, unknown>) => {
  const count = ['age_days_reference', 'age_reference_date', 'age_reference_source']
    .filter((field) => value[field] !== undefined && value[field] !== null).length;
  return count === 0 || count === 3;
};

export const resources = [
  { path: 'raspberries', table: 'raspberry', schema: raspberry,
    patch: raspberry.partial().refine(notEmpty, 'Informe pelo menos um campo.'),
    query: { active: booleanQuery.optional() }, operatorWrite: true },
  { path: 'lots', table: 'lot', schema: lot.refine(ageComplete, 'Informe idade, data e origem juntas.'),
    patch: lot.partial().refine(notEmpty, 'Informe pelo menos um campo.'),
    query: { archived: booleanQuery.optional() }, operatorWrite: false },
  { path: 'aviaries', table: 'aviary', schema: aviary,
    patch: aviary.partial().refine(notEmpty, 'Informe pelo menos um campo.'),
    query: { current_lot_id: queryId.optional() }, operatorWrite: false },
  { path: 'cameras', table: 'camera', schema: camera,
    patch: camera.partial().refine(notEmpty, 'Informe pelo menos um campo.'),
    query: { active: booleanQuery.optional(), raspberry_id: queryId.optional(), aviary_id: queryId.optional() },
    operatorWrite: true },
].map((resource) => ({
  ...resource,
  list: z.strictObject({
    limit: z.coerce.number().int().min(1).max(100).default(50),
    offset: z.coerce.number().int().min(0).max(1000000).default(0), ...resource.query,
  }),
}));

export const pathId = z.object({ id: queryId });
export const analysisFilter = z.strictObject({
  limit: z.coerce.number().int().min(1).max(100).default(50),
  offset: z.coerce.number().int().min(0).max(1000000).default(0),
  camera_id: queryId.optional(), aviary_id: queryId.optional(), lot_id: queryId.optional(),
  status: z.enum(['valido', 'imagem_inadequada', 'falha_processamento']).optional(),
  from: instant.optional(), to: instant.optional(),
}).refine((filter) => !filter.from || !filter.to || Date.parse(filter.from) <= Date.parse(filter.to),
  'O inicio deve anteceder o fim.');

const nullableCount = z.number().int().nonnegative().max(2147483647).nullable();
export const analysisItem = z.object({
  analise_id: z.uuid(),
  camera_id: z.union([id, z.string().regex(/^[1-9]\d*$/).refine((value) => Number(value) <= 2147483647)]),
  quadro_id: z.string().min(1).max(512),
  capturado_em: instant.nullable().optional(), processado_em: instant,
  status: z.enum(['valido', 'imagem_inadequada', 'falha_processamento']),
  motivo_status: z.string().min(1).max(4000).nullable().optional(),
  quantidade_aves_visiveis: nullableCount, total_atribuido_quadro: nullableCount,
  quantidade_sem_nivel: nullableCount, modelo_versao: z.string().min(1).max(512),
  contagens_por_nivel: z.record(z.string().min(1).max(100), nullableCount),
  percentuais_por_nivel: z.record(z.string().min(1).max(100), z.number().min(0).max(100).nullable()),
}).passthrough().superRefine((item, context) => {
  let valid = true;
  const counts = Object.values(item.contagens_por_nivel);
  const percentages = Object.values(item.percentuais_por_nivel);
  const levels = Object.keys(item.contagens_por_nivel);
  valid &&= levels.length === percentages.length && levels.every((level) => level in item.percentuais_por_nivel);
  if (item.status === 'valido') {
    valid &&= item.quantidade_aves_visiveis !== null && item.total_atribuido_quadro !== null
      && item.quantidade_sem_nivel !== null && counts.every((count) => count !== null);
    valid &&= counts.reduce<number>((sum, count) => sum + (count ?? 0), 0) === item.total_atribuido_quadro;
    valid &&= item.quantidade_aves_visiveis === (item.total_atribuido_quadro ?? 0) + (item.quantidade_sem_nivel ?? 0);
    valid &&= levels.every((level) => {
      const percentage = item.percentuais_por_nivel[level];
      if (!item.total_atribuido_quadro) return percentage === null;
      return percentage !== null && Math.abs(percentage - 100 * (item.contagens_por_nivel[level] ?? 0)
        / item.total_atribuido_quadro) <= 0.11;
    });
  } else {
    valid &&= Boolean(item.motivo_status?.trim()) && item.quantidade_aves_visiveis === null
      && item.total_atribuido_quadro === null && item.quantidade_sem_nivel === null
      && counts.every((count) => count === null) && percentages.every((value) => value === null);
  }
  if (!valid) context.addIssue({ code: 'custom', message: 'Contagens, percentuais ou status inconsistentes.' });
});

export const batchSchema = z.strictObject({ schema_version: z.literal(1), analyses: z.array(z.unknown()).max(500) });
