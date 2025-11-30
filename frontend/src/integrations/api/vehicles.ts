import { apiFetch } from "./client";
import { authHeaders } from "./auth";

export interface Vehicle {
  id: number;
  license_plate: string;
  owner_name: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface VehicleCreate {
  license_plate: string;
  owner_name: string;
  notes?: string | null;
  is_active?: boolean;
}

export interface VehiclesListParams {
  limit?: number;
  offset?: number;
  active_only?: boolean;
}

export const getVehicles = async (params: VehiclesListParams = {}): Promise<Vehicle[]> => {
  const { limit = 100, offset = 0, active_only = false } = params;
  const queryParams = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
    active_only: active_only.toString(),
  });

  return apiFetch<Vehicle[]>(`/vehicles?${queryParams.toString()}`, {
    method: "GET",
    headers: authHeaders(),
  });
};

export const createVehicle = async (payload: VehicleCreate): Promise<Vehicle> => {
  return apiFetch<Vehicle>("/vehicles", {
    method: "POST",
    headers: authHeaders(),
    json: payload,
  });
};

export const getActivePlates = async (): Promise<{ plates: string[] }> => {
  return apiFetch<{ plates: string[] }>("/vehicles/plates", {
    method: "GET",
    headers: authHeaders(),
  });
};

