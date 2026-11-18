import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// Organização por assunto. Os IDs e arquivos existentes preservam os links.
const sidebars: SidebarsConfig = {
  docsSidebar: [
    {type: 'doc', id: 'index', label: 'Comece aqui'},
    {
      type: 'category', label: 'Entenda a solução',
      link: {type: 'generated-index', slug: '/guia/solucao', description: 'Problema, público, escopo e critérios que orientam o projeto.'},
      items: [
        'sprint-1/proposta-de-solucao',
        'sprint-1/canvas-proposta-de-valor',
        {type: 'category', label: 'Quem vai usar', link: {type: 'doc', id: 'sprint-1/personas/index'}, items: [
          'sprint-1/personas/operadora-de-campo',
          'sprint-1/personas/profissional-de-producao',
          'sprint-1/personas/gestor-qualidade',
        ]},
        'sprint-1/requisitos',
        'sprint-1/pesquisa-comparativa-brasil-europa',
        'sprint-3/Analise Financeira/analise-financeira',
        'sprint-1/glossario',
      ],
    },
    {
      type: 'category', label: 'Como funciona',
      link: {type: 'generated-index', slug: '/guia/funcionamento', description: 'Câmeras, níveis do Jump Start e fluxo de processamento das imagens.'},
      items: [
        'sprint-2/arquitetura-preliminar',
        'sprint-2/proposta-solucao-cobertura',
        'sprint-2/visao-computacional/niveis-e-regra-de-contagem',
      ],
    },
    {
      type: 'category', label: 'Modelos, resultados e limites',
      link: {type: 'generated-index', slug: '/guia/modelos', description: 'Experimentos, métodos de avaliação, resultados e limites de cada abordagem.'},
      items: [
        {type: 'doc', id: 'sprint-2/index', label: 'Visão geral dos modelos'},
        'sprint-1/piloto-video-raiar',
        {type: 'category', label: 'RaiarNet: contagem por nível', link: {type: 'doc', id: 'sprint-2/visao-computacional/index'}, items: [
          'sprint-2/visao-computacional/dados-e-anotacao',
          'sprint-2/visao-computacional/tratamento-de-imagens',
          'sprint-2/visao-computacional/modelo-identificacao-do-zero',
          'sprint-2/visao-computacional/contagem-por-nivel',
        ]},
        'sprint-2/deteccao-de-aves',
        {type: 'category', label: 'PIOFlow e YOLOPIO', items: [
          'sprint-2/deteccao-e-contagem-de-galinhas',
          'sprint-4/pos-processamento-yolopio',
        ]},
        'sprint-4/yannet',
      ],
    },
    {
      type: 'category', label: 'Painel e acompanhamento',
      link: {type: 'generated-index', slug: '/guia/painel', description: 'Interface disponível, dados demonstrativos e propostas de evolução do acompanhamento.'},
      items: ['sprint-4/dashboard', 'sprint-4/alertas-e-dados-esperados', 'sprint-4/proposta-mapa-de-distribuicao'],
    },
    {
      type: 'category', label: 'Instalação e operação',
      link: {type: 'generated-index', slug: '/guia/operacao', description: 'Preparação do dispositivo, captura das imagens e passagem do teste para o ambiente real.'},
      items: [
        'sprint-3/provisionamento-raspberry-pi',
        'sprint-3/dvr-simulado-e-teste-na-pratica',
        'sprint-3/falhas-e-do-teste-para-producao',
      ],
    },
    {
      type: 'category', label: 'Referência técnica',
      link: {type: 'generated-index', slug: '/guia/referencia', description: 'API, armazenamento, contratos de integração e execução em containers para a equipe técnica.'},
      items: [
        'sprint-4/backend',
        'sprint-3/integracao-no-banco',
        'sprint-3/banco-de-dados',
        'sprint-1/dicionario-de-dados',
        'sprint-3/integracao-containers-no-no-de-borda',
        {type: 'category', label: 'Guias e exemplos de containers', link: {type: 'doc', id: 'sprint-3/exemplo-containers/index'}, items: [
          'sprint-3/exemplo-containers/guia-docker-para-iniciantes',
          'sprint-3/exemplo-containers/exemplos-de-codigo',
        ]},
      ],
    },
    {
      type: 'category', label: 'Histórico do desenvolvimento',
      link: {type: 'doc', id: 'historico'},
      items: [
        {type: 'category', label: 'Sprint 1', link: {type: 'generated-index', slug: '/category/sprint-1', description: 'Entregas da primeira sprint. Consulte também o índice completo no Histórico por sprint.'}, items: [
          {type: 'link', label: 'Proposta de solução', href: '/sprint-1/proposta-de-solucao'},
          {type: 'link', label: 'Requisitos', href: '/sprint-1/requisitos'},
        ]},
        {type: 'link', label: 'Modelos apresentados na Sprint 2', href: '/sprint-2'},
        {type: 'doc', id: 'sprint-3/index', label: 'Visão geral da entrega de borda (Sprint 3)'},
        {type: 'category', label: 'Sprint 4', link: {type: 'generated-index', slug: '/category/sprint-4', description: 'Entregas da quarta sprint. Consulte também o índice completo no Histórico por sprint.'}, items: [
          {type: 'link', label: 'Painel', href: '/sprint-4/dashboard'},
          {type: 'link', label: 'Backend', href: '/sprint-4/backend'},
          {type: 'link', label: 'YOLOPIO', href: '/sprint-4/pos-processamento-yolopio'},
          {type: 'link', label: 'YanNet', href: '/sprint-4/yannet'},
        ]},
      ],
    },
  ],
};

export default sidebars;
