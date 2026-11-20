import { useState } from 'react'
import { formatPrice } from '../format'
import PlatformLogo from './PlatformLogo'
import ProductImage from './ProductImage'

const STATUS = {
  exact: { label: 'Exact brand', className: 'status-exact' },
  alternative: { label: 'Other brand', className: 'status-alt' },
  alternative_available: { label: 'Other brand available', className: 'status-pending' },
  unavailable: { label: 'Not available', className: 'status-missing' },
}

function ChargeRow({ label, value, free, negative }) {
  const amount = Number(value)
  return (
    <div className="charge-row">
      <dt>{label}</dt>
      <dd className={negative && amount > 0 ? 'text-ok' : ''}>
        {free && amount === 0 ? 'Free' : negative && amount > 0 ? `− ${formatPrice(value)}` : formatPrice(value)}
      </dd>
    </div>
  )
}

function Line({ line, product, onAccept }) {
  const status = STATUS[line.status]
  const matched = line.matched_product
  return (
    <li className={`pline ${status.className}`}>
      <ProductImage product={matched || product} size="xs" />
      <div className="pline-main">
        <strong>{product.name}</strong>
        <span className={`status-chip ${status.className}`}>{status.label}</span>
        {matched && line.status !== 'exact' && (
          <span className="small">
            {matched.name} · {matched.quantity} at {formatPrice(line.unit_price)}
          </span>
        )}
        {line.status === 'alternative_available' && (
          <button className="btn-text" onClick={() => onAccept(line.product_id)}>Accept other brands for this item</button>
        )}
      </div>
      <div className="pline-price">
        {line.line_total !== null ? (
          <>
            <strong>{formatPrice(line.line_total)}</strong>
            <span className="small text-muted">{line.quantity} × {formatPrice(line.unit_price)}</span>
          </>
        ) : (
          <span className="small text-muted">not counted</span>
        )}
      </div>
    </li>
  )
}

/** One platform's complete-cart result: final payable, match counts, charges and item breakdown. */
export default function PlatformCartCard({ cart, productsById, savings, onAccept }) {
  const [open, setOpen] = useState(false)
  const { platform, charges } = cart
  const toFreeDelivery = Number(charges.delivery_fee) > 0 && charges.free_delivery_above !== null
    ? Number(charges.free_delivery_above) - Number(charges.subtotal)
    : 0

  const classes = ['pcard']
  if (cart.is_cheapest) classes.push('pcard-best')
  if (cart.is_highest) classes.push('pcard-high')
  if (!cart.is_complete) classes.push('pcard-incomplete')

  return (
    <article className={classes.join(' ')} data-platform={platform.slug}>
      {cart.is_cheapest && <span className="pcard-ribbon ribbon-best">★ Cheapest complete cart</span>}
      {cart.is_highest && <span className="pcard-ribbon ribbon-high">Highest complete cart</span>}
      {!cart.is_complete && <span className="pcard-ribbon ribbon-incomplete">Incomplete cart</span>}

      <header className="pcard-head">
        <PlatformLogo platform={platform} />
        <div>
          <strong>{platform.name}</strong>
          <span className="small text-muted">Delivery in {platform.delivery_eta}</span>
        </div>
      </header>

      <div className="pcard-total">
        <span className="small text-muted">{cart.is_complete ? 'Final payable' : `Payable for ${cart.available_items} of ${cart.requested_items} items`}</span>
        <strong>{formatPrice(cart.total)}</strong>
        {cart.is_cheapest && Number(savings) > 0 && <span className="savings-pop">You save {formatPrice(savings)} vs. the highest complete cart</span>}
        {cart.is_complete && !cart.is_cheapest && Number(cart.extra_vs_cheapest) > 0 && (
          <span className="extra-cost">{formatPrice(cart.extra_vs_cheapest)} more than the cheapest</span>
        )}
        {cart.is_complete && !cart.is_cheapest && Number(cart.extra_vs_cheapest) === 0 && (
          <span className="extra-cost">Same total as the cheapest</span>
        )}
        {!cart.is_complete && (
          <span className="text-warn small">
            {cart.would_complete_with_alternatives
              ? 'Complete if you accept other brands'
              : 'Not comparable: some items are missing'}
          </span>
        )}
      </div>

      <ul className="pcard-counts">
        <li><b>{cart.available_items}/{cart.requested_items}</b><span>available</span></li>
        <li className="count-exact"><b>{cart.exact_items}</b><span>exact brand</span></li>
        <li className="count-alt"><b>{cart.alternative_items + cart.alternative_available_items}</b><span>other brand</span></li>
        <li className="count-missing"><b>{cart.unavailable_items}</b><span>unavailable</span></li>
      </ul>

      <dl className="charges">
        <ChargeRow label="Item subtotal" value={charges.subtotal} />
        <ChargeRow label="Delivery fee" value={charges.delivery_fee} free />
        <ChargeRow label="Handling fee" value={charges.handling_fee} />
        <ChargeRow label="Platform fee" value={charges.platform_fee} />
        <ChargeRow label="Small-cart fee" value={charges.other_charges} />
        <ChargeRow label="Discount" value={charges.discount} negative />
        <div className="charge-row charge-total">
          <dt>Final payable</dt>
          <dd>{formatPrice(charges.total)}</dd>
        </div>
      </dl>
      {toFreeDelivery > 0 && <p className="small text-muted free-hint">Add {formatPrice(toFreeDelivery)} more for free delivery</p>}

      <button className="btn btn-secondary btn-block" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? 'Hide cart details' : 'View Cart Details'}
      </button>
      {open && (
        <ul className="pcard-lines">
          {cart.lines.map((line) => productsById[line.product_id] && (
            <Line key={line.product_id} line={line} product={productsById[line.product_id]} onAccept={onAccept} />
          ))}
        </ul>
      )}
    </article>
  )
}
