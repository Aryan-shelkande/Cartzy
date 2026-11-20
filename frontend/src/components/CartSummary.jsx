import { formatPrice } from '../format'
import ProductImage from './ProductImage'

const PREVIEW = 5

/** Sidebar shopping list: what's in it, the current best complete cart, and the main call to action. */
export default function CartSummary({ items, unitCount, comparison, onOpen }) {
  const { data, loading } = comparison
  if (unitCount === 0) {
    return (
      <aside className="cart-summary">
        <h3>My shopping list</h3>
        <p className="text-muted small summary-intro">
          Search for what you need and tap <strong>Add</strong>. We'll total the whole list on every app, fees included.
        </p>
        <button className="btn btn-primary btn-block btn-compare" disabled>Compare My Cart</button>
      </aside>
    )
  }

  return (
    <aside className="cart-summary cart-summary-active">
      <h3>My shopping list · {unitCount} item{unitCount === 1 ? '' : 's'}</h3>
      <ul className="summary-items">
        {items.slice(0, PREVIEW).map(({ product, quantity }) => (
          <li key={product.id}>
            <ProductImage product={product} size="xs" />
            <span className="summary-item-name">{product.name}</span>
            <span className="text-muted small">×{quantity}</span>
          </li>
        ))}
        {items.length > PREVIEW && <li className="text-muted small">+ {items.length - PREVIEW} more</li>}
      </ul>
      {loading && !data && <span className="spinner" />}
      {data && (data.cheapest_platform ? (
        <p className="summary-best">
          <span className="small text-muted">Best complete cart</span>
          <span><strong>{data.cheapest_platform.name}</strong> <span className="summary-total">{formatPrice(data.cheapest_total)}</span></span>
          {Number(data.savings) > 0 && <span className="text-ok small">Saves {formatPrice(data.savings)} vs. the priciest app</span>}
        </p>
      ) : (
        <p className="text-warn small">No single app has every item yet. Compare to see your options.</p>
      ))}
      <button className="btn btn-primary btn-block btn-compare" onClick={onOpen}>Compare My Cart →</button>
    </aside>
  )
}
