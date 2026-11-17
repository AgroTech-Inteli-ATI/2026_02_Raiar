export type ApiFailureKind = 'network' | 'unauthorized' | 'forbidden' | 'not-found' | 'server' | 'request';

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly kind: ApiFailureKind,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, '') ?? '';

export const isApiConfigured = Boolean(apiBaseUrl);

function apiUrl(path: string) {
  return `${apiBaseUrl}/${path.replace(/^\/+/, '')}`;
}

function errorForStatus(status: number) {
  if (status === 401) return new ApiRequestError('Não foi possível validar o acesso ao monitoramento.', 'unauthorized', status);
  if (status === 403) return new ApiRequestError('Seu acesso não permite consultar estas informações.', 'forbidden', status);
  if (status === 404) return new ApiRequestError('O conteúdo solicitado ainda não está disponível neste ambiente.', 'not-found', status);
  if (status >= 500) return new ApiRequestError('O serviço está temporariamente indisponível. Tente novamente em instantes.', 'server', status);
  return new ApiRequestError('Não foi possível carregar estas informações.', 'request', status);
}

export async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {headers: {Accept: 'application/json'}});
  } catch {
    throw new ApiRequestError('Não foi possível conectar ao monitoramento. Verifique se o serviço está disponível.', 'network');
  }

  if (!response.ok) throw errorForStatus(response.status);

  try {
    return await response.json() as T;
  } catch {
    throw new ApiRequestError('O serviço enviou uma resposta que não pôde ser lida.', 'request', response.status);
  }
}

type Page<T> = {data: T[]; pagination: {limit: number; offset: number; has_more: boolean}};

export async function getAllPages<T>(path: string): Promise<T[]> {
  const pageSize = 100;
  const rows: T[] = [];
  let offset = 0;

  while (true) {
    const page = await getJson<Page<T>>(`${path}?limit=${pageSize}&offset=${offset}`);
    if (!page || !Array.isArray(page.data) || !page.pagination || typeof page.pagination.has_more !== 'boolean') {
      throw new ApiRequestError('O serviço enviou uma lista em formato inesperado.', 'request');
    }
    rows.push(...page.data);
    if (!page.pagination.has_more) return rows;
    if (page.data.length === 0 || offset + page.data.length > 1_000_000) {
      throw new ApiRequestError('Não foi possível carregar a lista completa.', 'request');
    }
    offset += page.data.length;
  }
}
