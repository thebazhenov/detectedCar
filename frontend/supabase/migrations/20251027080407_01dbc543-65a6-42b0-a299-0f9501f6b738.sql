-- Add author field to access_events table
ALTER TABLE public.access_events
ADD COLUMN created_by uuid REFERENCES public.profiles(id);

-- Add index for better query performance
CREATE INDEX idx_access_events_created_by ON public.access_events(created_by);