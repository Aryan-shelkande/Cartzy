import { useEffect, useState } from 'react'
import { api } from './api'

/** Platform-wise totals for the cart; refetched whenever items or scope change. */
export function useCartComparison(cartId, items, filters) {
  const [state, setState] = useState({ data: null, loading: false, error: null })
  const key = JSON.stringify([cartId, items.map((i) => [i.product.id, i.quantity, i.accept_alternatives]), filters])

  useEffect(() => {
    if (!cartId || !filters.location || items.length === 0) {
      setState({ data: null, loading: false, error: null })
      return
    }
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    api.compareCart(cartId, filters)
      .then((data) => !cancelled && setState({ data, loading: false, error: null }))
      .catch((error) => !cancelled && setState({ data: null, loading: false, error }))
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return state
}
