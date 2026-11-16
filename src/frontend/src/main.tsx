import {createRoot} from 'react-dom/client';
import './styles/dashboard-tokens.css';

function FrontendShell() {
  return (
    <main>
      <h1>Raiar Orgânicos</h1>
      <p>O painel de acompanhamento será carregado aqui.</p>
    </main>
  );
}

const root = document.getElementById('root');

if (!root) {
  throw new Error('O elemento raiz do painel não foi encontrado.');
}

createRoot(root).render(<FrontendShell />);
