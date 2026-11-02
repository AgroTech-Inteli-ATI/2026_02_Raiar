-- Proposta de extensao do esquema inicial (schema.sql): analises enviadas pelo no de borda.
-- Requer as tabelas de schema.sql. Cria as tabelas de analise e a funcao de ingestao.

BEGIN;

CREATE TABLE public.analysis (
  id uuid NOT NULL,
  camera_id integer NOT NULL,
  aviary_id integer NOT NULL,
  lot_id integer,
  frame_id text NOT NULL,
  captured_at timestamp with time zone,
  processed_at timestamp with time zone NOT NULL,
  received_at timestamp with time zone NOT NULL DEFAULT now(),
  status character varying NOT NULL
    CHECK (status IN ('valido', 'imagem_inadequada', 'falha_processamento')),
  status_reason text,
  visible_birds integer,
  assigned_total integer,
  unassigned_birds integer,
  model_version text NOT NULL,
  payload jsonb NOT NULL,
  CONSTRAINT analysis_pkey PRIMARY KEY (id),
  CONSTRAINT analysis_camera_aviary_fkey
    FOREIGN KEY (camera_id, aviary_id)
    REFERENCES public.camera(id, aviary_id),
  CONSTRAINT analysis_lot_id_fkey
    FOREIGN KEY (lot_id) REFERENCES public.lot(id)
);

CREATE INDEX analysis_aviary_processed_idx
  ON public.analysis (aviary_id, processed_at DESC);

CREATE TABLE public.analysis_level_count (
  analysis_id uuid NOT NULL,
  level_id character varying NOT NULL,
  bird_count integer,
  percent numeric,
  CONSTRAINT analysis_level_count_pkey PRIMARY KEY (analysis_id, level_id),
  CONSTRAINT analysis_level_count_analysis_fkey
    FOREIGN KEY (analysis_id) REFERENCES public.analysis(id) ON DELETE CASCADE
);

-- Sem politicas: so a chave de servico (usada pela Edge Function) acessa estas tabelas.
ALTER TABLE public.analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_level_count ENABLE ROW LEVEL SECURITY;

-- Recebe {"schema_version": 1, "analyses": [...]} do `raiar-vision sync`.
-- Devolve {"accepted_analysis_ids": [...], "rejected": [{"id", "reason"}]}.
-- Reenvios sao idempotentes (ON CONFLICT DO NOTHING). Um item invalido ou de camera ainda nao
-- cadastrada e rejeitado sem derrubar o lote; o no o reenvia ate o cadastro existir.
CREATE FUNCTION public.ingest_analyses(batch jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
  item jsonb;
  item_id text;
  cam integer;
  av integer;
  lot integer;
  level record;
  accepted text[] := '{}';
  rejected jsonb := '[]'::jsonb;
BEGIN
  IF batch IS NULL OR batch->>'schema_version' IS DISTINCT FROM '1'
     OR jsonb_typeof(batch->'analyses') IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION 'Lote invalido: esperado schema_version 1 e lista analyses.';
  END IF;

  FOR item IN SELECT * FROM jsonb_array_elements(batch->'analyses') LOOP
    item_id := item->>'analise_id';
    BEGIN
      cam := (item->>'camera_id')::integer;
      SELECT c.aviary_id, a.current_lot_id INTO av, lot
        FROM camera c JOIN aviary a ON a.id = c.aviary_id
       WHERE c.id = cam;
      IF NOT FOUND THEN
        rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'camera_nao_cadastrada');
        CONTINUE;
      END IF;

      INSERT INTO analysis (
        id, camera_id, aviary_id, lot_id, frame_id, captured_at, processed_at, status,
        status_reason, visible_birds, assigned_total, unassigned_birds, model_version, payload
      ) VALUES (
        item_id::uuid, cam, av, lot, item->>'quadro_id',
        (item->>'capturado_em')::timestamptz, (item->>'processado_em')::timestamptz,
        item->>'status', item->>'motivo_status',
        (item->>'quantidade_aves_visiveis')::integer,
        (item->>'total_atribuido_quadro')::integer,
        (item->>'quantidade_sem_nivel')::integer,
        item->>'modelo_versao', item
      ) ON CONFLICT (id) DO NOTHING;

      IF FOUND THEN
        FOR level IN
          SELECT key AS level_id, value AS bird_count
            FROM jsonb_each(COALESCE(item->'contagens_por_nivel', '{}'::jsonb))
        LOOP
          INSERT INTO analysis_level_count (analysis_id, level_id, bird_count, percent)
          VALUES (
            item_id::uuid, level.level_id,
            CASE WHEN jsonb_typeof(level.bird_count) = 'number'
                 THEN (level.bird_count #>> '{}')::integer END,
            CASE WHEN jsonb_typeof(item->'percentuais_por_nivel'->level.level_id) = 'number'
                 THEN (item->'percentuais_por_nivel'->>level.level_id)::numeric END
          );
        END LOOP;
      END IF;
      accepted := accepted || item_id;
    EXCEPTION WHEN others THEN
      rejected := rejected || jsonb_build_object('id', item_id, 'reason', SQLERRM);
    END;
  END LOOP;

  RETURN jsonb_build_object('accepted_analysis_ids', to_jsonb(accepted), 'rejected', rejected);
END;
$$;

REVOKE ALL ON FUNCTION public.ingest_analyses(jsonb) FROM PUBLIC;

-- No Supabase, so a chave de servico executa a funcao; em Postgres puro o papel nao existe.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON FUNCTION public.ingest_analyses(jsonb) FROM anon, authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT EXECUTE ON FUNCTION public.ingest_analyses(jsonb) TO service_role;
  END IF;
END
$$;

COMMIT;
