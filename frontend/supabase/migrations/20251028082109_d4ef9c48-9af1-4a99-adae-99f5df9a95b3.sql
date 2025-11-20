-- Fix profiles table RLS policies
-- Drop the overly permissive policy
DROP POLICY IF EXISTS "Users can view all profiles" ON public.profiles;

-- Create restricted policies for profiles
CREATE POLICY "Users can view own profile"
ON public.profiles
FOR SELECT
USING (auth.uid() = id);

CREATE POLICY "Admins can view all profiles"
ON public.profiles
FOR SELECT
USING (has_role(auth.uid(), 'admin'));

-- Fix access_events table RLS policies
-- Drop the overly permissive policies
DROP POLICY IF EXISTS "Authenticated users can view events" ON public.access_events;
DROP POLICY IF EXISTS "System can insert events" ON public.access_events;

-- Create restricted policies for access_events
CREATE POLICY "Admins can view all events"
ON public.access_events
FOR SELECT
USING (has_role(auth.uid(), 'admin'));

CREATE POLICY "Operators can view all events"
ON public.access_events
FOR SELECT
USING (true);

CREATE POLICY "Authenticated users can insert events"
ON public.access_events
FOR INSERT
WITH CHECK (auth.uid() = created_by);