import {createRoot} from 'react-dom/client';
import App from './App';
import './styles/dashboard-tokens.css';

const root = document.getElementById('root');

if (!root) {
  throw new Error('O elemento raiz do painel não foi encontrado.');
}

createRoot(root).render(<App />);
