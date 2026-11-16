-- Campos de cadastro aprovados para a Sprint 4.
-- Aplicar em bancos existentes depois de schema.sql e 002_analises.sql.
-- O schema.sql atualizado ja inclui estes campos; neste caso a migracao preserva os valores.
-- Novos campos opcionais permanecem nulos; os padroes de active/timezone atendem linhas antigas.

BEGIN;

CREATE OR REPLACE FUNCTION public.is_valid_timezone(timezone_name text)
RETURNS boolean
LANGUAGE sql
STABLE
STRICT
SET search_path = pg_catalog
AS $$
  SELECT EXISTS (
    SELECT 1 FROM pg_catalog.pg_timezone_names WHERE name = timezone_name
  );
$$;

ALTER TABLE public.raspberry
  ADD COLUMN IF NOT EXISTS active boolean NOT NULL DEFAULT true;

ALTER TABLE public.aviary
  ADD COLUMN IF NOT EXISTS timezone text NOT NULL DEFAULT 'America/Sao_Paulo';

ALTER TABLE public.camera
  ADD COLUMN IF NOT EXISTS name character varying,
  ADD COLUMN IF NOT EXISTS active boolean NOT NULL DEFAULT true;

ALTER TABLE public.lot
  ADD COLUMN IF NOT EXISTS age_days_reference integer,
  ADD COLUMN IF NOT EXISTS age_reference_date date,
  ADD COLUMN IF NOT EXISTS age_reference_source text,
  ADD COLUMN IF NOT EXISTS archived_at timestamp with time zone;

-- PostgreSQL nao tem ADD CONSTRAINT IF NOT EXISTS. Conferir os nomes permite
-- executar esta migracao tambem sobre o esquema atualizado ou reaplica-la sem apagar dados.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_constraint
    WHERE conrelid = 'public.aviary'::regclass AND conname = 'aviary_timezone_check'
  ) THEN
    ALTER TABLE public.aviary
      ADD CONSTRAINT aviary_timezone_check CHECK (public.is_valid_timezone(timezone));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_constraint
    WHERE conrelid = 'public.camera'::regclass AND conname = 'camera_name_check'
  ) THEN
    ALTER TABLE public.camera
      ADD CONSTRAINT camera_name_check CHECK (name IS NULL OR btrim(name) <> '');
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_constraint
    WHERE conrelid = 'public.lot'::regclass AND conname = 'lot_age_days_reference_check'
  ) THEN
    ALTER TABLE public.lot
      ADD CONSTRAINT lot_age_days_reference_check CHECK (age_days_reference >= 0);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_constraint
    WHERE conrelid = 'public.lot'::regclass AND conname = 'lot_age_reference_check'
  ) THEN
    ALTER TABLE public.lot
      ADD CONSTRAINT lot_age_reference_check CHECK (
        (age_days_reference IS NULL AND age_reference_date IS NULL AND age_reference_source IS NULL)
        OR
        (age_days_reference IS NOT NULL AND age_reference_date IS NOT NULL
          AND age_reference_source IS NOT NULL AND btrim(age_reference_source) <> '')
      );
  END IF;
END;
$$;

COMMIT;
