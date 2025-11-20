import { useQuery } from "@tanstack/react-query";
import {
  DetectionSettings,
  getDetectionSettings,
  getPublicDetectionSettings,
} from "@/integrations/api/settings";

export const useAdminDetectionSettings = () => {
  return useQuery<DetectionSettings>({
    queryKey: ["detection-settings", "admin"],
    queryFn: getDetectionSettings,
    staleTime: 30_000,
  });
};

export const usePublicDetectionSettings = () => {
  return useQuery<DetectionSettings>({
    queryKey: ["detection-settings", "public"],
    queryFn: getPublicDetectionSettings,
    staleTime: 10_000,
    refetchInterval: 10_000,
  });
};


