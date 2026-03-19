import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Core imports
import './config/fonts'
import './i18n'
import './index.css'

import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
