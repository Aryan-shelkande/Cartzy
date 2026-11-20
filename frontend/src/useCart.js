import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import { load, save } from './storage'

const CART_KEY = 'cartzy.cartId'

/** Server-side shopping list; only its UUID is remembered in the browser. */
export function useCart(onError) {
  const [cart, setCart] = useState(null) // what the UI shows, including optimistic edits
  const [synced, setSynced] = useState(null) // last copy confirmed by the server
  const applyServer = useCallback((value) => {
    setSynced(value)
    setCart(value)
  }, [])
  const creating = useRef(null) // shared promise so rapid first clicks create one cart

  useEffect(() => {
    let cancelled = false
    async function init() {
      const savedId = load(CART_KEY)
      try {
        const existing = savedId ? await api.getCart(savedId) : null
        if (!cancelled) applyServer(existing)
        return
      } catch (err) {
        if (err.status !== 404) return onError(err)
      }
      // Saved cart no longer exists: start a fresh one lazily on first add.
      save(CART_KEY, null)
    }
    init()
    return () => { cancelled = true }
  }, [onError, applyServer])

  const ensureCartId = useCallback(async () => {
    if (cart) return cart.id
    creating.current ||= api.createCart().then((created) => {
      save(CART_KEY, created.id)
      return created.id
    })
    return creating.current
  }, [cart])

  // Requests run one at a time, and the server copy is applied only once the
  // queue is idle, so rapid clicks never act on (or flash back to) stale state.
  const queue = useRef(Promise.resolve())
  const pending = useRef(0)

  const run = useCallback((action, optimistic) => {
    if (optimistic) setCart((current) => current && optimistic(current))
    pending.current += 1
    queue.current = queue.current.then(async () => {
      let id
      try {
        id = await ensureCartId()
        const updated = await action(id)
        if (pending.current === 1) applyServer(updated)
        return true
      } catch (err) {
        onError(err)
        if (id) api.getCart(id).then(applyServer, () => {}) // undo the optimistic change
        return false
      } finally {
        pending.current -= 1
      }
    })
    return queue.current
  }, [ensureCartId, onError, applyServer])

  const items = cart?.items || []
  return {
    cartId: cart?.id,
    items,
    syncedItems: synced?.items || [],
    unitCount: items.reduce((sum, item) => sum + item.quantity, 0),
    quantityOf: (productId) => items.find((i) => i.product.id === productId)?.quantity || 0,
    add: (productId) => run((id) => api.addItem(id, productId)),
    setQuantity: (productId, qty) =>
      run(
        (id) => (qty < 1 ? api.removeItem(id, productId) : api.updateItem(id, productId, { quantity: qty })),
        (current) => ({
          ...current,
          items: current.items
            .map((i) => (i.product.id === productId ? { ...i, quantity: qty } : i))
            .filter((i) => i.quantity > 0),
        }),
      ),
    setAcceptAlternatives: (productId, accept) =>
      run(
        (id) => api.updateItem(id, productId, { accept_alternatives: accept }),
        (current) => ({
          ...current,
          items: current.items.map((i) => (i.product.id === productId ? { ...i, accept_alternatives: accept } : i)),
        }),
      ),
    changeBrand: (productId, newProductId) => run((id) => api.updateItem(id, productId, { product_id: newProductId })),
    remove: (productId) => run((id) => api.removeItem(id, productId)),
    clear: () => run((id) => api.clearCart(id)),
  }
}
