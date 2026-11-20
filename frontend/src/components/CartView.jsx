import { formatPrice } from '../format'
import PlatformCartCard from './PlatformCartCard'
import PlatformLogo from './PlatformLogo'
import ProductImage from './ProductImage'
import QuantityStepper from './QuantityStepper'

function ComparisonSummary({ comparison, pendingIds, onAcceptAll }) {
  const total = comparison.platforms.length
  const completable = comparison.platforms.filter((c) => c.would_complete_with_alternatives).length
  const { cheapest_platform: cheapest, highest_platform: highest, cheapest_exact_platform: cheapestExact } = comparison

  return (
    <div className="compare-summary">
      {cheapest ? (
        <div className="winner">
          <PlatformLogo platform={cheapest} size="lg" />
          <div className="winner-main">
            <span className="winner-label">Cheapest complete cart</span>
            <strong>{cheapest.name} · {formatPrice(comparison.cheapest_total)}</strong>
            <span className="winner-sub">Final payable, all fees and discounts included</span>
          </div>
          {highest && (
            <span className="savings-pop">
              🎉 Save {formatPrice(comparison.savings)} vs. {highest.name} ({formatPrice(comparison.highest_total)})
            </span>
          )}
        </div>
      ) : (
        <div className="notice notice-warn notice-big">
          <strong>No app has your complete list in {comparison.location.name}.</strong>
          <span>
            We don't rank incomplete carts as the cheapest, because their totals leave out the missing items.
            {completable > 0 && ` Accepting other brands would complete ${completable} cart${completable === 1 ? '' : 's'}.`}
          </span>
        </div>
      )}

      <p className="compare-meta">
        <span><b>{comparison.complete_count}</b> of {total} apps have everything</span>
        {cheapest && cheapestExact && cheapestExact.slug !== cheapest.slug && (
          <span>Cheapest with your exact brands: <b>{cheapestExact.name} {formatPrice(comparison.cheapest_exact_total)}</b></span>
        )}
        {pendingIds.length > 0 && (
          <button className="btn btn-secondary btn-sm" onClick={() => onAcceptAll(pendingIds)}>
            Accept other brands for {pendingIds.length} item{pendingIds.length === 1 ? '' : 's'} missing on some apps
          </button>
        )}
      </p>
    </div>
  )
}

function ListItem({ item, exactOn, platformCount, onQuantity, onRemove, onChangeBrand, onAcceptAlternatives, onCompare }) {
  const { product, quantity, accept_alternatives: accept, brand_options: brands = [] } = item
  return (
    <li className="cart-item">
      <button className="cart-item-info" onClick={() => onCompare(product.id)} aria-label={`Compare prices for ${product.name}`}>
        <ProductImage product={product} size="sm" />
        <span>
          <strong>{product.name}</strong>
          <span className="text-muted small">{product.quantity}</span>
          {exactOn !== null && (
            <span className={`small ${exactOn === platformCount ? 'text-ok' : 'text-warn'}`}>
              This brand on {exactOn}/{platformCount} apps
            </span>
          )}
        </span>
      </button>

      <div className="cart-item-controls">
        {brands.length > 1 ? (
          <label className="brand-select">
            <span className="small text-muted">Brand</span>
            <select value={product.id} onChange={(e) => onChangeBrand(product.id, Number(e.target.value))} aria-label={`Brand for ${product.generic_name || product.name}`}>
              {brands.map((b) => <option key={b.id} value={b.id}>{b.brand}</option>)}
            </select>
          </label>
        ) : (
          <span className="small text-muted">{product.brand}</span>
        )}
        <QuantityStepper small quantity={quantity} onChange={(q) => onQuantity(product.id, q)} />
        <button className="btn btn-link" onClick={() => onRemove(product)} aria-label={`Remove ${product.name}`}>Remove</button>
      </div>

      {brands.length > 1 && (
        <label className="alt-toggle">
          <input type="checkbox" checked={accept} onChange={(e) => onAcceptAlternatives(product.id, e.target.checked)} />
          <span>Accept another brand if {product.brand} is unavailable</span>
        </label>
      )}
    </li>
  )
}

export default function CartView({
  cart, comparison, onQuantity, onRemove, onClear, onCompare, onBack,
  onChangeBrand, onAcceptAlternatives, onAcceptAll,
}) {
  const { data, loading, error } = comparison
  const productsById = Object.fromEntries(cart.syncedItems.map((i) => [i.product.id, i.product]))
  const platformCount = data?.platforms.length || 0

  // On how many apps each product is available in the requested brand.
  const exactOn = (productId) => data
    ? data.platforms.filter((c) => c.lines.find((l) => l.product_id === productId)?.status === 'exact').length
    : null
  // Items with another brand waiting for acceptance on at least one app.
  const pendingIds = data
    ? [...new Set(data.platforms.flatMap((c) => c.lines.filter((l) => l.status === 'alternative_available').map((l) => l.product_id)))]
    : []

  if (cart.items.length === 0) {
    return (
      <section className="section cart-view">
        <div className="empty">
          <span className="empty-icon" aria-hidden="true">🧾</span>
          <h3>Your shopping list is empty</h3>
          <p>Add everything you need, then compare your whole cart across all {platformCount || 'seven'} apps.</p>
          <button className="btn btn-primary" onClick={onBack}>Start adding items</button>
        </div>
      </section>
    )
  }

  return (
    <section className="section cart-view">
      <div className="compare-head">
        <div>
          <h1>Compare my cart</h1>
          <p className="text-muted">
            {cart.items.length} item{cart.items.length === 1 ? '' : 's'} · {cart.unitCount} unit{cart.unitCount === 1 ? '' : 's'}
            {data && ` · ${data.location.name}, ${data.location.city}`}
          </p>
        </div>
        <div className="compare-head-actions">
          <button className="btn btn-secondary" onClick={onBack}>+ Add more items</button>
          <button className="btn btn-link" onClick={onClear}>Clear list</button>
        </div>
      </div>

      <div className="cart-layout">
        <div className="list-editor">
          <h2>Your list</h2>
          <p className="small text-muted">Change brands, quantities or substitutions. Results update instantly.</p>
          <ul className="cart-items">
            {cart.items.map((item) => (
              <ListItem
                key={item.product.id}
                item={item}
                exactOn={exactOn(item.product.id)}
                platformCount={platformCount}
                onQuantity={onQuantity}
                onRemove={onRemove}
                onChangeBrand={onChangeBrand}
                onAcceptAlternatives={onAcceptAlternatives}
                onCompare={onCompare}
              />
            ))}
          </ul>
        </div>

        <div className="results">
          {error && <p className="inline-error">{error.message}</p>}
          {loading && !data && <div className="loader"><span className="spinner" /> Comparing your cart on every app…</div>}
          {data && (
            <div className={loading ? 'is-refreshing' : ''}>
              <ComparisonSummary comparison={data} pendingIds={pendingIds} onAcceptAll={onAcceptAll} />
              <div className="platform-grid">
                {data.platforms.map((c) => (
                  <PlatformCartCard
                    key={c.platform.slug}
                    cart={c}
                    productsById={productsById}
                    savings={data.savings}
                    onAccept={(productId) => onAcceptAlternatives(productId, true)}
                  />
                ))}
              </div>
              {data.is_demo_data && (
                <p className="demo-note">
                  Demo data: prices, fees and discounts are simulated for demonstration and are not live platform prices.
                  Logos are trademarks of their owners; Cartzy is not affiliated with these platforms.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
