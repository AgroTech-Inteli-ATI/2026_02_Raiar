/**
 * Camada de dados da aba de alertas.
 * Sem VITE_API_BASE_URL, retorna exemplos locais. Com a variável definida,
 * consulta a API pública. Credenciais de serviço nunca devem ficar no navegador.
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
  };
};

export type AlertsResult = {
  alerts: AlertRecord[];
  source: 'demo' | 'api';
};

const demoAlerts: AlertRecord[] = [
  {
    id: 1,
    camera_id: 1,
    aviary_id: 1,
    datetime: '2026-11-12T09:42:00-03:00',
    alarm_type: 'Exemplo de tipo de alarme',
  },
  {
    id: 2,
    camera_id: 2,
    aviary_id: 1,
    datetime: '2026-11-12T08:15:00-03:00',
    alarm_type: 'Exemplo de tipo de alarme',
  },
  {
    id: 3,
    camera_id: 1,
    aviary_id: 1,
    datetime: '2026-11-11T17:05:00-03:00',
    alarm_type: 'Exemplo de tipo de alarme',
  },
];

export async function listAlerts(): Promise<AlertsResult> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

  if (!baseUrl) {
    return {alerts: demoAlerts, source: 'demo'};
  }

  const endpoint = new URL('alerts', `${baseUrl.replace(/\/+$/, '')}/`);
  const response = await fetch(endpoint);

  if (!response.ok) {
    throw new Error(`A API de alertas respondeu com HTTP ${response.status}.`);
  }

  const payload: unknown = await response.json();
  if (
    !payload ||
    typeof payload !== 'object' ||
    !('alerts' in payload) ||
    !Array.isArray(payload.alerts)
  ) {
    throw new Error('A resposta da API não contém a lista de alertas esperada.');
  }

  return {alerts: payload.alerts as AlertRecord[], source: 'api'};
}
