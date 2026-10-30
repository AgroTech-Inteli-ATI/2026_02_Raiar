-- Esquema inicial do banco de dados da Raiar (PostgreSQL).
-- Cria todas as tabelas em um banco que ainda nao tenha essas tabelas.

BEGIN;

CREATE TABLE public.raspberry (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  name character varying NOT NULL,
  hostname character varying NOT NULL UNIQUE,
  model character varying,
  CONSTRAINT raspberry_pkey PRIMARY KEY (id)
);

CREATE TABLE public.lot (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  name character varying NOT NULL,
  CONSTRAINT lot_pkey PRIMARY KEY (id)
);

CREATE TABLE public.aviary (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  name character varying NOT NULL,
  number integer NOT NULL,
  type character varying NOT NULL
    CHECK (type IN ('rearing', 'normal')),
  registration_date date NOT NULL DEFAULT CURRENT_DATE,
  current_lot_id integer UNIQUE,
  CONSTRAINT aviary_pkey PRIMARY KEY (id),
  CONSTRAINT aviary_current_lot_id_fkey
    FOREIGN KEY (current_lot_id) REFERENCES public.lot(id)
);

CREATE TABLE public.camera (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  raspberry_id integer NOT NULL,
  model character varying,
  aviary_id integer NOT NULL,
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
