import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // shared/catalog.json(백엔드와 같이 쓰는 목록)이 frontend 폴더 밖에 있다
    fs: { allow: ['..'] },
    // 개발 중에는 /api 요청을 백엔드로 넘긴다 → 같은 주소처럼 보여서 CORS 설정이 필요 없음
    proxy: { '/api': 'http://localhost:8001' },
  },
})
