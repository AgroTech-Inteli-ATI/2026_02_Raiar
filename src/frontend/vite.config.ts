import {defineConfig, loadEnv} from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendUrl = env.RAIAR_BACKEND_URL?.trim();
  const devToken = env.RAIAR_DEV_API_TOKEN?.trim();

  if (backendUrl) {
    const target = new URL(backendUrl);
    if (target.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(target.hostname)) {
      throw new Error('RAIAR_BACKEND_URL deve apontar para um backend HTTP local.');
    }
    if (target.username || target.password) {
      throw new Error('Não inclua credenciais em RAIAR_BACKEND_URL.');
    }

  }

  const proxy = backendUrl ? {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/api/, '') || '/',
        headers: devToken ? {Authorization: `Bearer ${devToken}`} : {},
      },
    } : undefined;

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy,
    },
    preview: {
      port: 4173,
      strictPort: true,
    },
  };
});
