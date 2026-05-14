// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  ssr: false,
  
  nitro: {
    devProxy: {
      '/api': {
        target: 'http://127.0.0.1:5000/api',
        changeOrigin: true,
      }
    }
  },

  app: {
    head: {
      title: 'YTConvert - Premium YouTube Downloader',
      meta: [
        { name: 'description', content: 'Conversor de YouTube para MP3/MP4 com alta qualidade e velocidade.' }
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap' },
        { rel: 'manifest', href: '/manifest.json' }
      ]

    }
  },

  css: ['~/assets/css/main.css']
})

