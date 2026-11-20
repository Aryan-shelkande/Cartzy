import { useCallback, useState } from 'react'

let nextId = 1

export function useToasts() {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, tone = 'info') => {
    const id = nextId++
    setToasts((list) => [...list.slice(-1), { id, message, tone }])
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 3200)
  }, [])
  return { toasts, push }
}
