import { HashRouter } from 'react-router-dom'
import { ReactNode } from 'react'

type RouterProviderProps = {
  children: ReactNode
}

export function RouterProvider({ children }: RouterProviderProps) {
  return <HashRouter>{children}</HashRouter>
}
