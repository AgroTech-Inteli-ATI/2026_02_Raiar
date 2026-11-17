import {ApiRequestError, getJson, isApiConfigured} from './apiClient';

/**
 * Camada de dados da aba de alertas.
 * Sem API configurada ou sem rota de alertas, retorna exemplos locais.
 */
export type BoundingBox = {x: number; y: number; width: number; height: number};

export type AlertRecord = {
  id: number;
  camera_id: number;
  aviary_id: number;
  datetime: string;
  alarm_type: string;
  image?: {
    url: string;
    alt: string;
    box: BoundingBox;
    illustration?: boolean;
  };
};

export type AlertsResult = {
  alerts: AlertRecord[];
  source: 'demo' | 'api';
  notice?: string;
};

const demoAlerts: AlertRecord[] = [
  {
    id: 1,
    camera_id: 1,
    aviary_id: 1,
    datetime: '2026-11-15T09:42:00-03:00',
    alarm_type: 'Possível amontoamento',
    image: {
      url: 'demo-frame',
      alt: 'Ilustração de exemplo de quadro de câmera com região destacada.',
      illustration: true,
      box: {x: 0.43, y: 0.27, width: 0.28, height: 0.46},
    },
  },
  {
    id: 2,
    camera_id: 2,
    aviary_id: 1,
    datetime: '2026-11-15T08:15:00-03:00',
    alarm_type: 'Aves sobrepostas',
  },
  {
    id: 3,
    camera_id: 3,
    aviary_id: 1,
    datetime: '2026-11-14T17:05:00-03:00',
    alarm_type: 'Possível amontoamento',
  },
];

export async function listAlerts(): Promise<AlertsResult> {
  if (!isApiConfigured) {
    return {alerts: demoAlerts, source: 'demo'};
  }

  try {
    const payload = await getJson<{alerts?: unknown}>('/alerts');
    if (!payload || !Array.isArray(payload.alerts)) {
      throw new ApiRequestError('O serviço enviou uma lista de avisos em formato inesperado.', 'request');
    }
    return {alerts: payload.alerts as AlertRecord[], source: 'api'};
  } catch (error) {
    if (error instanceof ApiRequestError && error.kind === 'not-found') {
      return {
        alerts: demoAlerts,
        source: 'demo',
        notice: 'Os avisos ainda não estão disponíveis neste ambiente.',
      };
    }
    throw error;
  }
}
