/**
 * Data adapter for the alerts view. Replace this demo implementation with the
 * backend client once the read endpoint and authentication flow are available.
 * The browser must never receive the Supabase service-role token.
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
    box?: BoundingBox;
  };
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

export async function listDemoAlerts(): Promise<AlertRecord[]> {
  // Keep the asynchronous boundary so swapping in the eventual API is local.
  return Promise.resolve(demoAlerts);
}
