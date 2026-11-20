import { useProducts } from '../useProducts'
import ProductCard from './ProductCard'

export function SkeletonCards({ count = 6 }) {
  return Array.from({ length: count }, (_, i) => <div key={i} className="product-card skeleton" aria-hidden="true" />)
}

/** Horizontal strip of products for a dashboard section. */
export default function ProductRail({ title, subtitle, icon, filters, query, cardActions }) {
  const { items, loading, error } = useProducts(filters, query)
  if (!loading && !error && items.length === 0) return null

  return (
    <section className="section">
      <div className="section-head">
        <h2><span aria-hidden="true">{icon}</span> {title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {error ? (
        <p className="inline-error">{error.message}</p>
      ) : (
        <div className="rail">
          {loading && items.length === 0
            ? <SkeletonCards />
            : items.map((p) => <ProductCard key={p.id} product={p} {...cardActions(p)} />)}
        </div>
      )}
    </section>
  )
}
