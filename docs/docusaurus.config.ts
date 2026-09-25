import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'Raiar',
  tagline: 'Documentação',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: 'https://your-docusaurus-site.example.com',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'AgroTech-Inteli-ATI',
  projectName: '2026_02_Raiar',

  onBrokenLinks: 'throw',

  // Habilita diagramas Mermaid (UML) nos .mdx via ```mermaid
  markdown: {
    mermaid: true,
    // Links e imagens quebrados entre páginas interrompem o build.
    hooks: {
      onBrokenMarkdownLinks: 'throw',
      onBrokenMarkdownImages: 'throw',
    },
  },
  themes: ['@docusaurus/theme-mermaid'],

  // Define o idioma do HTML e traduz os textos da interface do tema.
  i18n: {
    defaultLocale: 'pt-BR',
    locales: ['pt-BR'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: '/',
          sidebarPath: './sidebars.ts',
          editUrl:
            'https://github.com/AgroTech-Inteli-ATI/2026_02_Raiar/edit/develop/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // Tema único nas cores da Raiar: sem alternância claro/escuro.
    colorMode: {
      defaultMode: 'light',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    mermaid: {
      theme: {light: 'base', dark: 'base'},
      options: {
        themeVariables: {
          primaryColor: '#e9eff3',
          primaryBorderColor: '#254d69',
          primaryTextColor: '#212b36',
          secondaryColor: '#fff6d9',
          tertiaryColor: '#f4f6f8',
          lineColor: '#254d69',
          noteBkgColor: '#fff6d9',
          noteBorderColor: '#ffd043',
        },
      },
    },
    navbar: {
      title: 'Documentação',
      logo: {
        alt: 'Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          href: 'https://github.com/AgroTech-Inteli-ATI/2026_02_Raiar',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    
    prism: {
      theme: prismThemes.github,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
