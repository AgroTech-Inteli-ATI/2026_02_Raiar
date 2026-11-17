-- Executar em banco de teste com schema.sql e as migracoes aplicadas:
-- psql -v ON_ERROR_STOP=1 -f src/database/tests/dados_cadastro.sql
-- Todos os dados de teste sao revertidos ao final.

BEGIN;

CREATE FUNCTION pg_temp.expect_constraint_failure(
  statement text, expected_constraint text, expected_state text DEFAULT '23514'
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  actual_constraint text;
  actual_state text;
BEGIN
  BEGIN
    EXECUTE statement;
  EXCEPTION WHEN check_violation OR not_null_violation THEN
    GET STACKED DIAGNOSTICS
      actual_constraint = CONSTRAINT_NAME,
      actual_state = RETURNED_SQLSTATE;
    IF actual_state = expected_state AND actual_constraint = expected_constraint THEN
      RETURN;
    END IF;
    RAISE EXCEPTION 'Erro inesperado: estado %, constraint %', actual_state, actual_constraint;
  END;
  RAISE EXCEPTION 'Era esperado erro % na constraint %', expected_state, expected_constraint;
END;
$$;

DO $$
DECLARE
  device_id integer;
  aviary_id integer;
  lot_id integer;
  camera_id integer;
BEGIN
  -- Insercoes no formato anterior continuam funcionando sem inventar nomes ou idades.
  INSERT INTO public.raspberry (name, hostname, model)
    VALUES ('Dispositivo de teste', 'cadastro-test-' || txid_current(), 'RPi 4')
    RETURNING id INTO device_id;
  INSERT INTO public.lot (name) VALUES ('Lote de teste') RETURNING id INTO lot_id;
  INSERT INTO public.aviary (name, number, type, current_lot_id)
    VALUES ('Aviario de teste', 1, 'rearing', lot_id) RETURNING id INTO aviary_id;
  INSERT INTO public.camera (raspberry_id, aviary_id, model)
    VALUES (device_id, aviary_id, 'Camera de teste') RETURNING id INTO camera_id;

  IF (SELECT active FROM public.raspberry WHERE id = device_id) IS DISTINCT FROM true
     OR (SELECT active FROM public.camera WHERE id = camera_id) IS DISTINCT FROM true
     OR (SELECT timezone FROM public.aviary WHERE id = aviary_id)
       IS DISTINCT FROM 'America/Sao_Paulo' THEN
    RAISE EXCEPTION 'Padroes de cadastro incorretos';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.lot WHERE id = lot_id AND (
      age_days_reference IS NOT NULL OR age_reference_date IS NOT NULL
      OR age_reference_source IS NOT NULL OR archived_at IS NOT NULL
    )
  ) OR (SELECT name FROM public.camera WHERE id = camera_id) IS NOT NULL THEN
    RAISE EXCEPTION 'Campos desconhecidos devem permanecer nulos';
  END IF;

  -- A desativacao e o arquivamento preservam os registros e seus vinculos.
  UPDATE public.raspberry SET active = false WHERE id = device_id;
  UPDATE public.camera SET name = 'Camera norte', active = false WHERE id = camera_id;
  UPDATE public.lot SET
    age_days_reference = 0,
    age_reference_date = DATE '2026-11-01',
    age_reference_source = 'Registro ficticio revisado',
    archived_at = TIMESTAMPTZ '2026-11-12 10:00:00-03'
    WHERE id = lot_id;
  UPDATE public.aviary SET timezone = 'UTC' WHERE id = aviary_id;

  IF NOT EXISTS (
    SELECT 1 FROM public.camera c
    JOIN public.raspberry r ON r.id = c.raspberry_id
    JOIN public.aviary a ON a.id = c.aviary_id
    JOIN public.lot l ON l.id = a.current_lot_id
    WHERE c.id = camera_id AND NOT c.active AND NOT r.active
      AND c.name = 'Camera norte' AND a.timezone = 'UTC'
      AND l.age_days_reference = 0 AND l.age_reference_date = DATE '2026-11-01'
      AND l.age_reference_source = 'Registro ficticio revisado'
      AND l.archived_at = TIMESTAMPTZ '2026-11-12 13:00:00+00'
  ) THEN
    RAISE EXCEPTION 'Alterar os novos campos deve preservar valores e relacionamentos';
  END IF;

  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.raspberry SET active = NULL WHERE id = %s', device_id), '', '23502');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.camera SET active = NULL WHERE id = %s', camera_id), '', '23502');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.camera SET name = %L WHERE id = %s', '   ', camera_id),
    'camera_name_check');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.aviary SET timezone = NULL WHERE id = %s', aviary_id), '', '23502');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.aviary SET timezone = %L WHERE id = %s', 'Fuso/Inexistente', aviary_id),
    'aviary_timezone_check');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.aviary SET timezone = %L WHERE id = %s', '', aviary_id),
    'aviary_timezone_check');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.lot SET age_days_reference = -1 WHERE id = %s', lot_id),
    'lot_age_days_reference_check');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.lot SET age_reference_date = NULL WHERE id = %s', lot_id),
    'lot_age_reference_check');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.lot SET age_reference_source = NULL WHERE id = %s', lot_id),
    'lot_age_reference_check');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.lot SET age_reference_source = %L WHERE id = %s', '   ', lot_id),
    'lot_age_reference_check');
  PERFORM pg_temp.expect_constraint_failure(
    format('UPDATE public.lot SET age_days_reference = NULL WHERE id = %s', lot_id),
    'lot_age_reference_check');

  -- Restauracao do lote e remocao completa da referencia de idade sao permitidas.
  UPDATE public.lot SET age_days_reference = NULL, age_reference_date = NULL,
    age_reference_source = NULL, archived_at = NULL WHERE id = lot_id;
  UPDATE public.camera SET name = NULL, active = true WHERE id = camera_id;
  UPDATE public.raspberry SET active = true WHERE id = device_id;
END;
$$;

ROLLBACK;
