import { apiFetch } from "./client";
import { authHeaders } from "./auth";

export type CameraSourceType = "rtsp" | "file" | null;
export type DetectionTarget = "vehicles" | "people";

export interface WidgetPreferences {
  videoWidget: boolean;
  accessButton: boolean;
}

export interface DetectionSettings {
  sourceType: CameraSourceType;
  rtspUrl: string;
  videoPath: string;
  videoFileName: string;
  detectionTarget: DetectionTarget;
  detectionModel: string;
  widgets: WidgetPreferences;
}

export type DetectionSettingsUpdate = Partial<
  Omit<DetectionSettings, "widgets"> & { widgets: Partial<WidgetPreferences> }
>;

const adminHeaders = () => ({
  ...authHeaders(),
});

export const getDetectionSettings = async (): Promise<DetectionSettings> => {
  return apiFetch<DetectionSettings>("/settings/detection", {
    method: "GET",
    headers: adminHeaders(),
  });
};

export const getPublicDetectionSettings = async (): Promise<DetectionSettings> => {
  return apiFetch<DetectionSettings>("/settings/detection/public", {
    method: "GET",
    headers: adminHeaders(),
  });
};

export const updateDetectionSettings = async (
  payload: DetectionSettingsUpdate,
): Promise<DetectionSettings> => {
  return apiFetch<DetectionSettings>("/settings/detection", {
    method: "PATCH",
    headers: adminHeaders(),
    json: payload,
  });
};


