import { formatPrice } from '../format'
import ProductImage from './ProductImage'
import QuantityStepper from './QuantityStepper'

export default function ProductCard({ product, platformCount, quantity, onAdd, onQuantity, onCompare }) {
  const available = product.available_count > 0
  const savings = Number(product.savings)

  return (
    <article className={`product-card ${available ? '' : 'is-unavailable'} ${quantity > 0 ? 'in-list' : ''}`}>
      {savings > 0 && <span className="deal-badge">Save up to {formatPrice(savings)}</span>}
      <button className="product-card-body" onClick={() => onCompare(product.id)} aria-label={`Compare prices for ${product.name}`}>
        <ProductImage product={product} />
        <span className="product-brand">{product.brand}</span>
        <h3 className="product-name">{product.name}</h3>
        <span className="product-qty">
          {product.quantity}
          {product.alternatives_count > 0 && (
            <span className="brands-pill">+{product.alternatives_count} brand{product.alternatives_count === 1 ? '' : 's'}</span>
          )}
        </span>
      </button>

      <div className="product-card-footer">
        <div className="product-price">
          {available ? (
            <>
              <span className="price-from">from</span>
              <strong>{formatPrice(product.min_price)}</strong>
              {Number(product.mrp) > Number(product.min_price) && <s>{formatPrice(product.mrp)}</s>}
            </>
          ) : (
            <strong className="text-muted">Unavailable</strong>
          )}
          <span className="availability">
            on {product.available_count}/{platformCount} apps
          </span>
        </div>
        {quantity > 0
          ? <QuantityStepper small quantity={quantity} onChange={(q) => onQuantity(product.id, q)} />
          : <button className="btn btn-add" onClick={() => onAdd(product)}>Add</button>}
      </div>
    </article>
  )
}
