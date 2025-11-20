import { useQuery } from "@tanstack/react-query";
import { DemoVideoInfo, getPublicDemoVideo } from "@/integrations/api/demo";

export const useDemoVideo = () => {
  return useQuery<DemoVideoInfo | null>({
    queryKey: ["demo-video"],
    queryFn: getPublicDemoVideo,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
};


