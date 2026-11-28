import { defineConfig } from 'vitepress';

const repository = 'https://github.com/jmmana/sqltoviz';

export default defineConfig({
  title: 'SqlToViz',
  base: '/sqltoviz/docs/',
  locales: {
    root: {
      label: 'English',
      lang: 'en',
      description: 'SqlToViz SDK and project documentation',
      themeConfig: {
        nav: [
          { text: 'Playground', link: 'https://jmmana.github.io/sqltoviz/#play' },
          { text: 'Roadmap', link: '/roadmap' },
        ],
        sidebar: [
          { text: 'Overview', link: '/' },
          { text: 'Architecture', link: '/architecture' },
          { text: 'SQL input', link: '/sql-input-scope' },
          { text: 'Alpha release', link: '/alpha-release' },
        ],
      },
    },
    es: {
      label: 'Español',
      lang: 'es',
      description: 'Documentación del proyecto y los SDK de SqlToViz',
      themeConfig: {
        nav: [
          { text: 'Demostración', link: 'https://jmmana.github.io/sqltoviz/#play' },
          { text: 'Hoja de ruta', link: '/roadmap' },
        ],
        sidebar: [{ text: 'Inicio', link: '/es/' }],
      },
    },
  },
  themeConfig: {
    socialLinks: [{ icon: 'github', link: repository }],
  },
});
