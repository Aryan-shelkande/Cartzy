import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import { celebrate } from './confetti'
import { formatPrice } from './format'
import { load, save } from './storage'
import { useCart } from './useCart'
import { useCartComparison } from './useCartComparison'
import CartSummary from './components/CartSummary'
import CartView from './components/CartView'
import CategoryBar from './components/CategoryBar'
import ComparisonDrawer from './components/ComparisonDrawer'
import Header from './components/Header'
import Hero from './components/Hero'
import ProductBrowser from './components/ProductBrowser'
import ProductRail from './components/ProductRail'
import { Toasts } from './components/Toasts'
import { useToasts } from './useToasts'

const LOCATION_KEY = 'cartzy.location'
const SAVINGS_MILESTONES = [50, 100, 250, 500]

export default function App() {
  const [meta, setMeta] = useState({ locations: [], categories: [], platforms: [], loading: true, error: null })
  const [location, setLocation] = useState(() => load(LOCATION_KEY))
  const [selectedPlatforms, setSelectedPlatforms] = useState([]) // empty = all platforms
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [ordering, setOrdering] = useState('popular')
  const [availableOnly, setAvailableOnly] = useState(false)
  const [view, setView] = useState('shop')
  const [compareId, setCompareId] = useState(null)
  const { toasts, push } = useToasts()

  const onError = useCallback((err) => push(err.message, 'error'), [push])
  const cart = useCart(onError)

  const fetchMeta = useCallback(() => {
    Promise.all([api.locations(), api.categories(), api.platforms()])
      .then(([locations, categories, platforms]) => {
        setMeta({ locations, categories, platforms, loading: false, error: null })
        setLocation((current) => (locations.some((l) => l.slug === current) ? current : locations[0]?.slug))
      })
      .catch((error) => setMeta((m) => ({ ...m, loading: false, error })))
  }, [])
  useEffect(fetchMeta, [fetchMeta])
  const retryMeta = () => {
    setMeta((m) => ({ ...m, loading: true, error: null }))
    fetchMeta()
  }

  useEffect(() => save(LOCATION_KEY, location || null), [location])

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), 250)
    return () => clearTimeout(t)
  }, [searchInput])

  const filters = useMemo(() => ({ location, platforms: selectedPlatforms }), [location, selectedPlatforms])
  const comparison = useCartComparison(cart.cartId, cart.syncedItems, filters)

  // Celebrate once each time cart savings cross a new milestone, but only after
  // the user has edited the cart this session (not when a saved cart loads).
  const milestone = useRef(0)
  const cartTouched = useRef(false)
  useEffect(() => {
    const savings = Number(comparison.data?.savings || 0)
    const reached = SAVINGS_MILESTONES.filter((m) => savings >= m).pop() || 0
    if (reached > milestone.current && cartTouched.current) {
      celebrate()
      push(`🎉 You're saving ${formatPrice(savings)} by choosing ${comparison.data.cheapest_platform.name}!`, 'success')
    }
    milestone.current = reached
  }, [comparison.data, push])

  const locationObj = meta.locations.find((l) => l.slug === location)
  const visiblePlatforms = selectedPlatforms.length || meta.platforms.length

  const togglePlatform = (slug) => {
    const current = selectedPlatforms.length ? selectedPlatforms : meta.platforms.map((p) => p.slug)
    const next = current.includes(slug) ? current.filter((s) => s !== slug) : [...current, slug]
    if (next.length === 0) return push('Keep at least one platform selected.')
    setSelectedPlatforms(next.length === meta.platforms.length ? [] : next)
  }

  const addToCart = async (product) => {
    cartTouched.current = true
    if (await cart.add(product.id)) push(`Added ${product.name} to your list`, 'success')
  }
  const removeFromCart = async (product) => {
    cartTouched.current = true
    if (await cart.remove(product.id)) push(`Removed ${product.name}`)
  }
  const setQuantity = (productId, qty) => {
    cartTouched.current = true
    return cart.setQuantity(productId, qty)
  }
  const changeBrand = async (productId, newProductId) => {
    cartTouched.current = true
    const brand = cart.items.find((i) => i.product.id === productId)?.brand_options.find((b) => b.id === newProductId)?.brand
    if (await cart.changeBrand(productId, newProductId)) push(`Switched to ${brand}`, 'success')
  }
  const setAcceptAlternatives = (productId, accept) => {
    cartTouched.current = true
    return cart.setAcceptAlternatives(productId, accept)
  }
  const acceptAllAlternatives = async (productIds) => {
    cartTouched.current = true
    const results = await Promise.all(productIds.map((id) => cart.setAcceptAlternatives(id, true)))
    if (results.every(Boolean)) push('Other brands accepted. Totals updated.', 'success')
  }
  const quickSearch = (term) => {
    setSearchInput(term)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const cardActions = (product) => ({
    platformCount: visiblePlatforms,
    quantity: cart.quantityOf(product.id),
    onAdd: addToCart,
    onQuantity: setQuantity,
    onCompare: setCompareId,
  })

  const resetFilters = () => {
    setSearchInput('')
    setSearch('')
    setCategory('')
    setSelectedPlatforms([])
    setAvailableOnly(false)
  }

  const goShop = () => setView('shop')
  const isBrowsing = Boolean(search || category)
  const categoryName = meta.categories.find((c) => c.slug === category)?.name

  if (meta.loading && !meta.locations.length) {
    return <div className="fullscreen"><span className="spinner" /> Loading Cartzy…</div>
  }
  if (meta.error) {
    return (
      <div className="fullscreen">
        <div className="empty">
          <span className="empty-icon" aria-hidden="true">🔌</span>
          <h3>Couldn't load Cartzy</h3>
          <p>{meta.error.message}</p>
          <button className="btn btn-primary" onClick={retryMeta}>Try again</button>
        </div>
      </div>
    )
  }

  return (
    <>
      <Header
        locations={meta.locations}
        location={location}
        onLocationChange={setLocation}
        search={searchInput}
        onSearch={(value) => { setSearchInput(value); setView('shop') }}
        cartCount={cart.unitCount}
        onOpenCart={() => setView('cart')}
        onHome={() => { resetFilters(); goShop() }}
      />

      <div className="demo-banner">
        <strong>Demo data</strong> — prices, availability, fees and discounts are simulated for demonstration and are not live platform prices.
      </div>

      <main className="page" key={view}>
        {view === 'cart' ? (
          <>
            <button className="btn btn-link back" onClick={goShop}>← Back to shopping</button>
            <CartView
              cart={cart}
              comparison={comparison}
              onQuantity={setQuantity}
              onRemove={removeFromCart}
              onClear={async () => { if (await cart.clear()) push('Shopping list cleared') }}
              onCompare={setCompareId}
              onBack={goShop}
              onChangeBrand={changeBrand}
              onAcceptAlternatives={setAcceptAlternatives}
              onAcceptAll={acceptAllAlternatives}
            />
          </>
        ) : (
          <div className="shop-layout">
            <div className="shop-main">
              {!isBrowsing && <Hero platformCount={meta.platforms.length} locationName={locationObj?.name} onQuickSearch={quickSearch} />}
              <CategoryBar categories={meta.categories} active={category} onSelect={setCategory} />

              {!isBrowsing && (
                <>
                  <ProductRail title="Best deals right now" subtitle="Biggest gap between the cheapest and priciest app" icon="🔥"
                    filters={filters} query={{ ordering: 'savings', available: 'true', page_size: 10 }} cardActions={cardActions} />
                  <ProductRail title="Featured" icon="⭐" filters={filters}
                    query={{ featured: 'true', ordering: 'popular', page_size: 10 }} cardActions={cardActions} />
                </>
              )}

              <ProductBrowser
                title={search ? `Results for “${search}”` : categoryName || 'Popular groceries'}
                filters={filters}
                query={{ search, category }}
                platforms={meta.platforms}
                selectedPlatforms={selectedPlatforms}
                onTogglePlatform={togglePlatform}
                ordering={ordering}
                onOrdering={setOrdering}
                availableOnly={availableOnly}
                onAvailableOnly={setAvailableOnly}
                onReset={resetFilters}
                cardActions={cardActions}
              />
            </div>
            <CartSummary items={cart.items} unitCount={cart.unitCount} comparison={comparison} onOpen={() => setView('cart')} />
          </div>
        )}
      </main>

      {compareId && (
        <ComparisonDrawer
          productId={compareId}
          filters={filters}
          quantity={cart.quantityOf(compareId)}
          quantityOf={cart.quantityOf}
          onAdd={addToCart}
          onQuantity={setQuantity}
          onOpenProduct={setCompareId}
          onClose={() => setCompareId(null)}
        />
      )}

      <Toasts toasts={toasts} />
    </>
  )
}
