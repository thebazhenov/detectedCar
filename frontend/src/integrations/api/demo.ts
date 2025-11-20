import { apiFetch } from "./client";

export interface DemoVideoInfo {
  file_name: string;
  file_url: string;
}

export const getPublicDemoVideo = async (): Promise<DemoVideoInfo | null> => {
  try {
    return await apiFetch<DemoVideoInfo>("/demo/video/public", {
      method: "GET",
    });
  } catch (error) {
    if ((error as any)?.status === 404) {
      return null;
    }
    throw error;
  }
};


