import { useCallback, useEffect, useState } from 'react'
import { api } from './api'

const INITIAL = { items: [], count: 0, page: 1, hasMore: false, loading: true, error: null }

/** Paginated product list for the given location/platform scope and query params. */
export function useProducts(filters, query) {
  const [state, setState] = useState(INITIAL)
  const key = JSON.stringify([filters, query])

  useEffect(() => {
    if (!filters.location) return
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    api.products(filters, query)
      .then((data) => {
        if (!cancelled) setState({ items: data.results, count: data.count, page: 1, hasMore: !!data.next, loading: false, error: null })
      })
      .catch((error) => !cancelled && setState({ ...INITIAL, loading: false, error }))
    return () => { cancelled = true }
    // `key` captures filters and query by value.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const loadMore = useCallback(() => {
    const page = state.page + 1
    setState((s) => ({ ...s, loading: true }))
    api.products(filters, { ...query, page })
      .then((data) => setState((s) => ({ ...s, items: [...s.items, ...data.results], page, hasMore: !!data.next, loading: false })))
      .catch((error) => setState((s) => ({ ...s, loading: false, error })))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, state.page])

  return { ...state, loadMore }
}
