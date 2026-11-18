import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {type: 'doc', id: 'index', label: 'A solução e seu escopo'},
    'funcionamento',
    'resultados',
    'painel',
    {
      type: 'category', label: 'Referência técnica',
      link: {type: 'generated-index', slug: '/guia/referencia', description: 'Procedimentos, contratos e reprodução dos experimentos para a equipe técnica.'},
      items: [
        'tecnico/dispositivo', 'tecnico/captura-operacao', 'tecnico/servicos',
        'tecnico/backend', 'tecnico/dados', 'tecnico/requisitos',
        'tecnico/raiarnet', 'tecnico/yolo', 'tecnico/pio', 'tecnico/yannet',
      ],
    },
    {
      type: 'category', label: 'Material de apoio',
      link: {type: 'generated-index', slug: '/apoio', description: 'Público, referências, custos e material de aprendizagem do projeto.'},
      items: [
        'apoio/perfis', 'apoio/canvas', 'apoio/bem-estar', 'apoio/financeiro',
        'apoio/docker', 'apoio/glossario', 'apoio/historico',
      ],
    },
  ],
};

export default sidebars;
