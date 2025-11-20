-- Create table for temporary vehicle passes
CREATE TABLE public.temporary_passes (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  license_plate TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  entries_used INTEGER NOT NULL DEFAULT 0,
  created_by UUID REFERENCES public.profiles(id),
  CONSTRAINT entries_limit CHECK (entries_used >= 0 AND entries_used <= 2)
);

-- Enable RLS
ALTER TABLE public.temporary_passes ENABLE ROW LEVEL SECURITY;

-- Policy for authenticated users to view temporary passes
CREATE POLICY "Authenticated users can view temporary passes"
ON public.temporary_passes
FOR SELECT
USING (true);

-- Policy for authenticated users to create temporary passes
CREATE POLICY "Authenticated users can create temporary passes"
ON public.temporary_passes
FOR INSERT
WITH CHECK (auth.uid() = created_by);

-- Policy for system to update entries_used
CREATE POLICY "System can update temporary passes"
ON public.temporary_passes
FOR UPDATE
USING (true);

-- Create index for faster lookups
CREATE INDEX idx_temporary_passes_license_plate ON public.temporary_passes(license_plate);
CREATE INDEX idx_temporary_passes_expires_at ON public.temporary_passes(expires_at);

-- Create function to clean up expired passes
CREATE OR REPLACE FUNCTION public.cleanup_expired_passes()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  DELETE FROM public.temporary_passes
  WHERE expires_at < now() OR entries_used >= 2;
END;
$$;