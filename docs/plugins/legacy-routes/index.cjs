const routes = require('../../legacy-routes.json');

// Redireciona rotas antigas sem manter cópias dos documentos consolidados.
module.exports = function legacyRoutes(context) {
  const additional = [
    ['/guia/solucao', '/'], ['/guia/funcionamento', '/funcionamento'],
    ['/guia/modelos', '/resultados'], ['/guia/painel', '/painel'],
    ['/guia/operacao', '/tecnico/captura-operacao'],
    ['/category/sprint-1', '/apoio/historico'], ['/category/sprint-4', '/apoio/historico'],
  ].map(([from, to]) => ({from, to, hashes: {}}));
  return {
    name: 'raiar-legacy-routes',
    async contentLoaded({actions}) {
      for (const [index, entry] of [...routes, ...additional].entries()) {
        const destination = context.siteConfig.baseUrl + entry.to.replace(/^\//, '');
        const component = await actions.createData(`redirect-${index}.js`, `
import React, {useEffect} from 'react';
const destination = ${JSON.stringify(destination)};
const hashes = ${JSON.stringify(entry.hashes)};
const initialAnchor = ${JSON.stringify(entry.anchor || '')};
export default function LegacyRedirect() {
  useEffect(() => {
    const raw = decodeURIComponent(window.location.hash.slice(1));
    const anchor = raw ? (hashes[raw] || raw) : initialAnchor;
    window.location.replace(destination + (anchor ? '#' + anchor : ''));
  }, []);
  return React.createElement('main', {style: {padding: '2rem'}},
    React.createElement('p', null, 'Este conteúdo foi reunido na documentação por assunto.'),
    React.createElement('a', {href: destination + (initialAnchor ? '#' + initialAnchor : '')}, 'Abrir conteúdo consolidado'));
}
`);
        actions.addRoute({path: context.siteConfig.baseUrl + entry.from.replace(/^\//, ''), component, exact: true});
      }
    },
  };
};
