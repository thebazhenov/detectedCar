-- Fix temporary_passes table RLS policies
-- These policies were too permissive, allowing all authenticated users to view and modify all passes

-- Drop the overly permissive SELECT policy
DROP POLICY IF EXISTS "Authenticated users can view temporary passes" ON public.temporary_passes;

-- Create restricted SELECT policy - users can only view their own passes, admins can view all
CREATE POLICY "Users can view own temporary passes"
ON public.temporary_passes
FOR SELECT
USING (auth.uid() = created_by OR has_role(auth.uid(), 'admin'::app_role));

-- Drop the overly permissive UPDATE policy
DROP POLICY IF EXISTS "System can update temporary passes" ON public.temporary_passes;

-- Create restricted UPDATE policy - only creators and admins can update passes
CREATE POLICY "Creators and admins can update passes"
ON public.temporary_passes
FOR UPDATE
USING (auth.uid() = created_by OR has_role(auth.uid(), 'admin'::app_role));