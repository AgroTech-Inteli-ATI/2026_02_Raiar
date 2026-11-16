-- Historico de ocupacao: intervalos [started_at, ended_at), com fim aberto para o lote atual.
-- Nao inventa datas anteriores: o cadastro existente e conhecido apenas desde esta migracao.

BEGIN;

-- O snapshot e a instalacao do trigger precisam observar o mesmo cadastro atual.
LOCK TABLE public.aviary IN SHARE ROW EXCLUSIVE MODE;

CREATE TABLE public.aviary_lot_assignment (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  aviary_id integer NOT NULL REFERENCES public.aviary(id),
  lot_id integer NOT NULL REFERENCES public.lot(id),
  started_at timestamptz NOT NULL,
  ended_at timestamptz,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  origin text NOT NULL DEFAULT 'assignment' CHECK (origin IN ('assignment', 'migration_snapshot')),
  CONSTRAINT aviary_lot_assignment_period_check CHECK (
    isfinite(started_at) AND (ended_at IS NULL OR (isfinite(ended_at) AND ended_at > started_at))
  ),
  CONSTRAINT aviary_lot_assignment_context_key UNIQUE (id, aviary_id, lot_id),
  -- Ranges de um unico ID usam GiST nativo, sem exigir a extensao btree_gist.
  CONSTRAINT aviary_lot_assignment_aviary_overlap EXCLUDE USING gist (
    int8range(aviary_id::bigint, aviary_id::bigint, '[]') WITH &&,
    tstzrange(started_at, ended_at, '[)') WITH &&
  ),
  CONSTRAINT aviary_lot_assignment_lot_overlap EXCLUDE USING gist (
    int8range(lot_id::bigint, lot_id::bigint, '[]') WITH &&,
    tstzrange(started_at, ended_at, '[)') WITH &&
  )
);

CREATE INDEX aviary_lot_assignment_capture_idx
  ON public.aviary_lot_assignment (aviary_id, started_at DESC);
ALTER TABLE public.aviary_lot_assignment ENABLE ROW LEVEL SECURITY;

INSERT INTO public.aviary_lot_assignment (aviary_id, lot_id, started_at, origin)
  SELECT id, current_lot_id, clock_timestamp(), 'migration_snapshot'
  FROM public.aviary WHERE current_lot_id IS NOT NULL;

ALTER TABLE public.analysis
  ADD COLUMN lot_assignment_id integer,
  ADD COLUMN lot_association_status text NOT NULL DEFAULT 'legacy_unverified',
  ADD CONSTRAINT analysis_lot_assignment_fkey
    FOREIGN KEY (lot_assignment_id, aviary_id, lot_id)
    REFERENCES public.aviary_lot_assignment (id, aviary_id, lot_id),
  ADD CONSTRAINT analysis_lot_association_check CHECK (
    (lot_association_status = 'matched' AND lot_assignment_id IS NOT NULL
      AND lot_id IS NOT NULL AND captured_at IS NOT NULL)
    OR (lot_association_status IN ('no_capture_time', 'no_occupancy')
      AND lot_assignment_id IS NULL AND lot_id IS NULL)
    OR (lot_association_status = 'legacy_unverified' AND lot_assignment_id IS NULL)
  );

CREATE INDEX analysis_lot_assignment_capture_idx
  ON public.analysis (lot_assignment_id, captured_at);

-- O trigger cobre tambem cadastros e PATCH antigos, SQL direto e chamadas via Supabase.
CREATE FUNCTION public.record_aviary_lot_assignment()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
  changed_at timestamptz;
  latest public.aviary_lot_assignment;
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.current_lot_id IS NOT DISTINCT FROM OLD.current_lot_id THEN
    RETURN NEW;
  END IF;
  changed_at := COALESCE(
    NULLIF(current_setting('raiar.lot_effective_at', true), '')::timestamptz,
    clock_timestamp()
  );
  IF NOT isfinite(changed_at) OR changed_at > clock_timestamp() THEN
    RAISE EXCEPTION 'Instante de ocupacao invalido.' USING ERRCODE = '23514';
  END IF;

  SELECT * INTO latest FROM public.aviary_lot_assignment
    WHERE aviary_id = NEW.id ORDER BY started_at DESC LIMIT 1;
  IF FOUND AND (
    (latest.ended_at IS NULL AND changed_at <= latest.started_at)
    OR (latest.ended_at IS NOT NULL AND changed_at < latest.ended_at)
  ) THEN
    RAISE EXCEPTION 'A troca nao pode reescrever uma ocupacao anterior.' USING ERRCODE = '23514';
  END IF;
  IF latest.id IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.analysis
      WHERE lot_assignment_id = latest.id AND captured_at >= changed_at
  ) THEN
    RAISE EXCEPTION 'A troca invalidaria analises ja vinculadas a esta ocupacao.' USING ERRCODE = '23514';
  END IF;

  UPDATE public.aviary_lot_assignment SET ended_at = changed_at
    WHERE aviary_id = NEW.id AND ended_at IS NULL;
  IF NEW.current_lot_id IS NOT NULL THEN
    INSERT INTO public.aviary_lot_assignment (aviary_id, lot_id, started_at)
      VALUES (NEW.id, NEW.current_lot_id, changed_at);
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER aviary_lot_assignment_record
  AFTER INSERT OR UPDATE OF current_lot_id ON public.aviary
  FOR EACH ROW EXECUTE FUNCTION public.record_aviary_lot_assignment();

CREATE FUNCTION public.assign_aviary_lot(
  p_aviary_id integer, p_lot_id integer, p_effective_at timestamptz
)
RETURNS public.aviary
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
  result public.aviary;
  previous_effective_at text;
BEGIN
  IF p_effective_at IS NULL OR NOT isfinite(p_effective_at) OR p_effective_at > clock_timestamp() THEN
    RAISE EXCEPTION 'Instante de ocupacao invalido.' USING ERRCODE = '23514';
  END IF;
  SELECT * INTO result FROM public.aviary WHERE id = p_aviary_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Aviario inexistente.' USING ERRCODE = 'P0002';
  END IF;
  previous_effective_at := current_setting('raiar.lot_effective_at', true);
  PERFORM set_config('raiar.lot_effective_at', p_effective_at::text, true);
  UPDATE public.aviary SET current_lot_id = p_lot_id WHERE id = p_aviary_id RETURNING * INTO result;
  PERFORM set_config('raiar.lot_effective_at', COALESCE(previous_effective_at, ''), true);
  RETURN result;
EXCEPTION WHEN others THEN
  PERFORM set_config('raiar.lot_effective_at', COALESCE(previous_effective_at, ''), true);
  RAISE;
END;
$$;

CREATE OR REPLACE FUNCTION public.ingest_analyses(batch jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
  item jsonb;
  item_id text;
  cam integer;
  av integer;
  lot integer;
  assignment integer;
  association_status text;
  captured timestamptz;
  camera_active boolean;
  device_active boolean;
  existing_payload jsonb;
  level record;
  accepted text[] := '{}';
  rejected jsonb := '[]'::jsonb;
BEGIN
  IF batch IS NULL OR batch->>'schema_version' IS DISTINCT FROM '1'
     OR jsonb_typeof(batch->'analyses') IS DISTINCT FROM 'array'
     OR jsonb_array_length(batch->'analyses') > 500 THEN
    RAISE EXCEPTION 'Lote invalido: esperado schema_version 1 e no maximo 500 analises.';
  END IF;

  FOR item IN SELECT * FROM jsonb_array_elements(batch->'analyses') LOOP
    item_id := item->>'analise_id';
    BEGIN
      SELECT payload INTO existing_payload FROM public.analysis WHERE id = item_id::uuid;
      IF FOUND THEN
        IF existing_payload = item THEN
          accepted := accepted || item_id;
        ELSE
          rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'analise_id_conflitante');
        END IF;
        CONTINUE;
      END IF;

      cam := (item->>'camera_id')::integer;
      SELECT c.aviary_id, c.active, r.active INTO av, camera_active, device_active
        FROM public.camera c JOIN public.aviary a ON a.id = c.aviary_id
        JOIN public.raspberry r ON r.id = c.raspberry_id
        WHERE c.id = cam FOR SHARE OF c, r, a;
      IF NOT FOUND THEN
        rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'camera_nao_cadastrada');
        CONTINUE;
      END IF;
      IF NOT camera_active OR NOT device_active THEN
        rejected := rejected || jsonb_build_object('id', item_id, 'reason',
          CASE WHEN NOT camera_active THEN 'camera_inativa' ELSE 'dispositivo_inativo' END);
        CONTINUE;
      END IF;

      lot := NULL;
      assignment := NULL;
      IF item->>'capturado_em' IS NOT NULL
         AND item->>'capturado_em' !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' THEN
        rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'capturado_em_invalido');
        CONTINUE;
      END IF;
      captured := (item->>'capturado_em')::timestamptz;
      IF captured IS NULL THEN
        association_status := 'no_capture_time';
      ELSE
        SELECT h.id, h.lot_id INTO assignment, lot FROM public.aviary_lot_assignment h
          WHERE h.aviary_id = av AND h.started_at <= captured
            AND (h.ended_at IS NULL OR captured < h.ended_at);
        association_status := CASE WHEN FOUND THEN 'matched' ELSE 'no_occupancy' END;
      END IF;
      IF lot IS NOT NULL AND item->>'lote_id' IS NOT NULL
         AND item->>'lote_id' <> lot::text THEN
        rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'lote_divergente');
        CONTINUE;
      END IF;

      INSERT INTO public.analysis (
        id, camera_id, aviary_id, lot_id, lot_assignment_id, lot_association_status,
        frame_id, captured_at, processed_at, status,
        status_reason, visible_birds, assigned_total, unassigned_birds, model_version, payload
      ) VALUES (
        item_id::uuid, cam, av, lot, assignment, association_status, item->>'quadro_id', captured,
        (item->>'processado_em')::timestamptz, item->>'status', item->>'motivo_status',
        (item->>'quantidade_aves_visiveis')::integer,
        (item->>'total_atribuido_quadro')::integer,
        (item->>'quantidade_sem_nivel')::integer, item->>'modelo_versao', item
      ) ON CONFLICT (id) DO UPDATE SET id = EXCLUDED.id
        WHERE analysis.payload = EXCLUDED.payload;
      IF NOT FOUND THEN
        rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'analise_id_conflitante');
        CONTINUE;
      END IF;

      FOR level IN
        SELECT key AS level_id, value AS bird_count
        FROM jsonb_each(COALESCE(item->'contagens_por_nivel', '{}'::jsonb))
      LOOP
        INSERT INTO public.analysis_level_count (analysis_id, level_id, bird_count, percent)
        VALUES (
          item_id::uuid, level.level_id,
          CASE WHEN jsonb_typeof(level.bird_count) = 'number'
            THEN (level.bird_count #>> '{}')::integer END,
          CASE WHEN jsonb_typeof(item->'percentuais_por_nivel'->level.level_id) = 'number'
            THEN (item->'percentuais_por_nivel'->>level.level_id)::numeric END
        ) ON CONFLICT (analysis_id, level_id) DO NOTHING;
      END LOOP;
      accepted := accepted || item_id;
    EXCEPTION WHEN others THEN
      rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'item_invalido');
    END;
  END LOOP;
  RETURN jsonb_build_object('accepted_analysis_ids', to_jsonb(accepted), 'rejected', rejected);
END;
$$;

REVOKE ALL ON FUNCTION public.record_aviary_lot_assignment() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.assign_aviary_lot(integer, integer, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ingest_analyses(jsonb) FROM PUBLIC;

DO $$
BEGIN
  -- Supabase pode conceder EXECUTE explicitamente por default privileges.
  -- Revogar apenas PUBLIC nao remove esses acessos ao RPC administrativo.
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON FUNCTION public.assign_aviary_lot(integer, integer, timestamptz) FROM anon;
    REVOKE ALL ON FUNCTION public.record_aviary_lot_assignment() FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON FUNCTION public.assign_aviary_lot(integer, integer, timestamptz) FROM authenticated;
    REVOKE ALL ON FUNCTION public.record_aviary_lot_assignment() FROM authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT SELECT, INSERT, UPDATE ON public.aviary_lot_assignment TO service_role;
    GRANT USAGE, SELECT ON SEQUENCE public.aviary_lot_assignment_id_seq TO service_role;
    GRANT EXECUTE ON FUNCTION public.assign_aviary_lot(integer, integer, timestamptz) TO service_role;
  END IF;
END;
$$;

COMMIT;
