-- O servidor nao conhece a fila offline do no. Cada ID de camera pertence a um
-- unico aviario, mesmo antes de receber a primeira analise.
BEGIN;

CREATE FUNCTION public.prevent_camera_aviary_change()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF NEW.aviary_id IS DISTINCT FROM OLD.aviary_id THEN
    RAISE EXCEPTION 'O aviario de uma camera e fixo. Cadastre outro ID para mudar de aviario.'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER camera_aviary_immutable
  BEFORE UPDATE OF aviary_id ON public.camera
  FOR EACH ROW EXECUTE FUNCTION public.prevent_camera_aviary_change();

REVOKE ALL ON FUNCTION public.prevent_camera_aviary_change() FROM PUBLIC;

COMMIT;
