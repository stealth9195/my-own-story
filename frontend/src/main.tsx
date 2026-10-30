import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import Demo from './Demo.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* (실험) ?demo 이면 사물 위치 비교 화면 */}
    {location.search.includes('demo') ? <Demo /> : <App />}
  </StrictMode>,
)
