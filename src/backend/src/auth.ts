import { createHash, timingSafeEqual } from 'node:crypto';
import { ApiError } from './errors.js';

export type Principal = { subject: string; role: 'gestor' | 'operador' };
export type UserVerifier = (token: string) => Promise<Principal | null>;

export function tokensEqual(first: string, second: string) {
  const hash = (value: string) => createHash('sha256').update(value).digest();
  return timingSafeEqual(hash(first), hash(second));
}

export function supabaseUserVerifier(url: string, key: string): UserVerifier {
  return async (token) => {
    let response: Response;
    try {
      response = await fetch(new URL('/auth/v1/user', url), {
        headers: { apikey: key, Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(5000),
        redirect: 'error',
      });
    } catch {
      throw new ApiError(503, 'auth_unavailable', 'Autenticacao temporariamente indisponivel.');
    }
    if (response.status === 401 || response.status === 403) return null;
    if (!response.ok) throw new ApiError(503, 'auth_unavailable', 'Autenticacao indisponivel.');
    const user = await response.json() as { id?: unknown; app_metadata?: { role?: unknown } };
    const role = user.app_metadata?.role;
    if (typeof user.id !== 'string' || (role !== 'gestor' && role !== 'operador')) return null;
    return { subject: user.id, role };
  };
}
