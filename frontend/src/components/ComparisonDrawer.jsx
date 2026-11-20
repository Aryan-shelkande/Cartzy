import { useEffect, useState } from 'react'
import { api } from '../api'
import { formatPrice, timeAgo } from '../format'
import PlatformLogo from './PlatformLogo'
import ProductImage from './ProductImage'
import QuantityStepper from './QuantityStepper'

export default function ComparisonDrawer({ productId, filters, quantity, quantityOf, onAdd, onQuantity, onOpenProduct, onClose }) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const key = JSON.stringify(filters)

  useEffect(() => {
    let cancelled = false
    setState({ data: null, loading: true, error: null })
    api.compareProduct(productId, filters)
      .then((data) => !cancelled && setState({ data, loading: false, error: null }))
      .catch((error) => !cancelled && setState({ data: null, loading: false, error }))
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId, key])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const { data, loading, error } = state
  const product = data?.product
  const savings = Number(data?.savings || 0)

  return (
    <div className="overlay" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Price comparison" onClick={(e) => e.stopPropagation()}>
        <button className="drawer-close" onClick={onClose} aria-label="Close">×</button>

        {loading && <div className="loader"><span className="spinner" /> Comparing prices…</div>}
        {error && <p className="inline-error">{error.message}</p>}

        {product && (
          <>
            <div className="drawer-product">
              <ProductImage product={product} size="lg" />
              <div>
                <span className="product-brand">{product.brand} · {product.category.name}</span>
                <h2>{product.name}</h2>
                <p className="text-muted">{product.quantity} · MRP {formatPrice(product.mrp)} · SKU {product.sku}</p>
              </div>
            </div>

            {data.available_count > 0 ? (
              <div className="drawer-summary">
                <div>
                  <span className="text-muted">Best price in {data.location.name}</span>
                  <strong className="big-price">{formatPrice(data.cheapest_price)}</strong>
                </div>
                {savings > 0 && (
                  <div className="savings-pop">
                    <span aria-hidden="true">✨</span> Save {formatPrice(savings)} vs. highest
                  </div>
                )}
              </div>
            ) : (
              <div className="notice notice-warn">This exact product is not available on any selected platform in {data.location.name}. Other brands are listed below, and we never swap them in without asking.</div>
            )}

            <ul className="offers">
              {data.offers.map((o) => (
                <li key={o.platform.slug} className={`offer ${o.is_cheapest ? 'offer-best' : ''} ${o.is_available ? '' : 'offer-out'}`}>
                  <PlatformLogo platform={o.platform} size="sm" />
                  <div className="offer-main">
                    <strong>{o.platform.name}</strong>
                    <span className="text-muted">
                      {o.is_available ? `${o.platform.delivery_eta} · updated ${timeAgo(o.updated_at)}` : o.price ? 'Out of stock' : 'Not listed'}
                    </span>
                  </div>
                  <div className="offer-price">
                    {o.is_available ? formatPrice(o.price) : '—'}
                    {o.is_cheapest && <span className="best-tag">Cheapest</span>}
                  </div>
                </li>
              ))}
            </ul>

            <div className="drawer-actions">
              {quantity > 0
                ? <><span>In your list</span><QuantityStepper quantity={quantity} onChange={(q) => onQuantity(product.id, q)} /></>
                : <button className="btn btn-primary btn-block" onClick={() => onAdd(product)}>Add to shopping list</button>}
            </div>
            {data.alternatives.length > 0 && (
              <section className="other-brands">
                <h3>Other brands · {product.generic_name || product.name} {product.quantity}</h3>
                <ul>
                  {data.alternatives.map((alt) => (
                    <li key={alt.id}>
                      <button className="other-brand-info" onClick={() => onOpenProduct(alt.id)}>
                        <ProductImage product={alt} size="sm" />
                        <span>
                          <strong>{alt.brand}</strong>
                          <span className="small text-muted">{alt.name}</span>
                          <span className="small">
                            {alt.available_count > 0 ? <>from <b>{formatPrice(alt.min_price)}</b> · {alt.available_count} apps</> : 'Unavailable here'}
                          </span>
                        </span>
                      </button>
                      {quantityOf(alt.id) > 0
                        ? <span className="small text-ok">In list ×{quantityOf(alt.id)}</span>
                        : <button className="btn btn-add" onClick={() => onAdd(alt)}>Add</button>}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {data.is_demo_data && <p className="demo-note">Demo data: prices are simulated for demonstration and are not live platform prices.</p>}
          </>
        )}
      </aside>
    </div>
  )
}
