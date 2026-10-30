import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import Demo from './Demo.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* 개발 중에만: ?demo 이면 장면·읽기 화면 확인 페이지 (배포판에서는 꺼짐) */}
    {import.meta.env.DEV && location.search.includes('demo') ? <Demo /> : <App />}
  </StrictMode>,
)
