-- Fix search_path for cleanup function
CREATE OR REPLACE FUNCTION public.cleanup_expired_passes()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
BEGIN
  DELETE FROM public.temporary_passes
  WHERE expires_at < now() OR entries_used >= 2;
END;
$$;