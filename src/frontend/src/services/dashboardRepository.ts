import {getAllPages, getJson} from './apiClient';

export type CameraRecord = {
  id: number;
  name: string | null;
  aviary_id: number;
};

export type AviaryRecord = {
  id: number;
  name: string;
  number: number;
};

export async function listCameras() {
  return getAllPages<CameraRecord>('/cameras');
}

export async function listAviaries() {
  return getAllPages<AviaryRecord>('/aviaries');
}

export async function checkApiHealth() {
  try {
    const result = await getJson<{status?: string}>('/health');
    return result?.status === 'ok';
  } catch {
    return false;
  }
}
