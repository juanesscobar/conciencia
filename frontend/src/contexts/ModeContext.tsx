import { createContext, useContext, useState, ReactNode } from 'react'

export type Mode = 'operator' | 'client'

interface ModeContextValue {
  mode: Mode
  setMode: (m: Mode) => void
  isOperator: boolean
}

const ModeContext = createContext<ModeContextValue>({
  mode: 'operator',
  setMode: () => {},
  isOperator: true,
})

export function ModeProvider({ children, defaultMode }: { children: ReactNode; defaultMode: Mode }) {
  const [mode, setModeState] = useState<Mode>(() => {
    try {
      const saved = localStorage.getItem('conciencia_mode') as Mode | null
      return saved === 'operator' || saved === 'client' ? saved : defaultMode
    } catch {
      return defaultMode
    }
  })

  const setMode = (m: Mode) => {
    try { localStorage.setItem('conciencia_mode', m) } catch { /* noop */ }
    setModeState(m)
  }

  return (
    <ModeContext.Provider value={{ mode, setMode, isOperator: mode === 'operator' }}>
      {children}
    </ModeContext.Provider>
  )
}

export const useMode = () => useContext(ModeContext)
