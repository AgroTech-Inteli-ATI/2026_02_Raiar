-- Consolida a ingestao utilizada pela API e pela Edge Function existente.
-- Desativacao impede novas analises; reenvios identicos ja persistidos continuam confirmados.
-- A associacao ao lote ainda usa current_lot_id; o historico de ocupacao e uma entrega posterior.

BEGIN;

CREATE OR REPLACE FUNCTION public.ingest_analyses(batch jsonb)
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
      SELECT payload INTO existing_payload FROM analysis WHERE id = item_id::uuid;
      IF FOUND THEN
        IF existing_payload = item THEN
          accepted := accepted || item_id;
        ELSE
          rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'analise_id_conflitante');
        END IF;
        CONTINUE;
      END IF;

      cam := (item->>'camera_id')::integer;
      SELECT c.aviary_id, a.current_lot_id, c.active, r.active
        INTO av, lot, camera_active, device_active
        FROM camera c JOIN aviary a ON a.id = c.aviary_id
        JOIN raspberry r ON r.id = c.raspberry_id
        WHERE c.id = cam FOR SHARE OF c, r;
      IF NOT FOUND THEN
        rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'camera_nao_cadastrada');
        CONTINUE;
      END IF;
      IF NOT camera_active OR NOT device_active THEN
        rejected := rejected || jsonb_build_object('id', item_id, 'reason',
          CASE WHEN NOT camera_active THEN 'camera_inativa' ELSE 'dispositivo_inativo' END);
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
        INSERT INTO analysis_level_count (analysis_id, level_id, bird_count, percent)
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
      -- A API nao precisa receber mensagens SQL internas para corrigir o item.
      rejected := rejected || jsonb_build_object('id', item_id, 'reason', 'item_invalido');
    END;
  END LOOP;
  RETURN jsonb_build_object('accepted_analysis_ids', to_jsonb(accepted), 'rejected', rejected);
END;
$$;

REVOKE ALL ON FUNCTION public.ingest_analyses(jsonb) FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON FUNCTION public.ingest_analyses(jsonb) FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON FUNCTION public.ingest_analyses(jsonb) FROM authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT EXECUTE ON FUNCTION public.ingest_analyses(jsonb) TO service_role;
  END IF;
END;
$$;

COMMIT;
