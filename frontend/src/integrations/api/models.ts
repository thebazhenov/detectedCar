import { apiFetch } from "./client";
import { authHeaders } from "./auth";

export interface YoloModelInfo {
  file_name: string;
  display_name: string;
  size_mb: number;
}

export const getYoloModels = async (): Promise<YoloModelInfo[]> => {
  return apiFetch<YoloModelInfo[]>("/models/yolo", {
    method: "GET",
    headers: authHeaders(),
  });
};


