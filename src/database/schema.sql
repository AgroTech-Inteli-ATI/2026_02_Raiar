-- Esquema inicial do banco de dados da Raiar (PostgreSQL).
-- Cria todas as tabelas em um banco que ainda nao tenha essas tabelas.

BEGIN;

-- Aceita nomes de fuso reconhecidos pelo PostgreSQL, inclusive America/Sao_Paulo e UTC.
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

CREATE TABLE public.raspberry (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  name character varying NOT NULL,
  hostname character varying NOT NULL UNIQUE,
  model character varying,
  active boolean NOT NULL DEFAULT true,
  CONSTRAINT raspberry_pkey PRIMARY KEY (id)
);

CREATE TABLE public.lot (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  name character varying NOT NULL,
  age_days_reference integer,
  age_reference_date date,
  age_reference_source text,
  archived_at timestamp with time zone,
  CONSTRAINT lot_age_days_reference_check CHECK (age_days_reference >= 0),
  CONSTRAINT lot_age_reference_check CHECK (
    (age_days_reference IS NULL AND age_reference_date IS NULL AND age_reference_source IS NULL)
    OR
    (age_days_reference IS NOT NULL AND age_reference_date IS NOT NULL
      AND age_reference_source IS NOT NULL AND btrim(age_reference_source) <> '')
  ),
  CONSTRAINT lot_pkey PRIMARY KEY (id)
);

CREATE TABLE public.aviary (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  name character varying NOT NULL,
  number integer NOT NULL,
  box_identifiers text[],
  type character varying NOT NULL
    CHECK (type IN ('rearing', 'normal')),
  registration_date date NOT NULL DEFAULT CURRENT_DATE,
  timezone text NOT NULL DEFAULT 'America/Sao_Paulo',
  current_lot_id integer UNIQUE,
  CONSTRAINT aviary_timezone_check CHECK (public.is_valid_timezone(timezone)),
  CONSTRAINT aviary_pkey PRIMARY KEY (id),
  CONSTRAINT aviary_current_lot_id_fkey
    FOREIGN KEY (current_lot_id) REFERENCES public.lot(id)
);

CREATE TABLE public.camera (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  name character varying,
  raspberry_id integer NOT NULL,
  model character varying,
  aviary_id integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  CONSTRAINT camera_name_check CHECK (name IS NULL OR btrim(name) <> ''),
  CONSTRAINT camera_pkey PRIMARY KEY (id),
  CONSTRAINT camera_raspberry_id_fkey
    FOREIGN KEY (raspberry_id) REFERENCES public.raspberry(id),
  CONSTRAINT camera_aviary_id_fkey
    FOREIGN KEY (aviary_id) REFERENCES public.aviary(id),
  CONSTRAINT camera_id_aviary_id_key UNIQUE (id, aviary_id)
);

CREATE TABLE public.alerts (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  camera_id integer NOT NULL,
  aviary_id integer NOT NULL,
  datetime timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  alarm_type character varying NOT NULL,
  CONSTRAINT alerts_pkey PRIMARY KEY (id),
  CONSTRAINT alerts_aviary_id_fkey
    FOREIGN KEY (aviary_id) REFERENCES public.aviary(id),
  CONSTRAINT alerts_camera_aviary_fkey
    FOREIGN KEY (camera_id, aviary_id)
    REFERENCES public.camera(id, aviary_id)
);

COMMIT;
