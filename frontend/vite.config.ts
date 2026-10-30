import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // PWA: 휴대폰 홈 화면에 설치되고, 한 번 받은 앱 파일·그림·소리는 기기에 저장(캐시)해 두고 쓴다
    VitePWA({
      registerType: 'autoUpdate',  // 새 버전을 배포하면 다음에 열 때 알아서 새 버전으로 바뀜
      manifest: {
        name: '나만의 이야기',
        short_name: '나만의 이야기',
        description: '아이가 고르면 이어지는 AI 구연동화',
        lang: 'ko',
        display: 'standalone',  // 설치하면 주소창 없이 앱처럼 열림
        background_color: '#fff8ee',
        theme_color: '#ff8a3d',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // 앱 파일(js·css·html·아이콘)만 미리 받아 둔다. 그림·소리는 처음 쓸 때 받아 저장
        globPatterns: ['**/*.{js,css,html,svg,png}'],
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => /^\/(img|sound|bgm)\//.test(url.pathname),
            handler: 'CacheFirst',
            options: {
              cacheName: 'assets',
              expiration: { maxEntries: 300 },
              cacheableResponse: { statuses: [0, 200] },
              rangeRequests: true,  // 음악·효과음은 브라우저가 나눠서 요청한다(특히 아이폰)
            },
          },
          // 이야기·음성 API 는 저장하지 않는다(서명된 이야기·음성은 IndexedDB 가 맡음)
          { urlPattern: ({ url }) => url.pathname.startsWith('/api/'), handler: 'NetworkOnly' },
        ],
      },
    }),
  ],
  server: {
    // shared/catalog.json(백엔드와 같이 쓰는 목록)이 frontend 폴더 밖에 있다
    fs: { allow: ['..'] },
    // 개발 중에는 /api 요청을 백엔드로 넘긴다 → 같은 주소처럼 보여서 CORS 설정이 필요 없음
    proxy: { '/api': 'http://localhost:8001' },
  },
})
