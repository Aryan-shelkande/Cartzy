import { useProducts } from '../useProducts'
import ProductCard from './ProductCard'
import { SkeletonCards } from './ProductRail'

const SORT_OPTIONS = [
  ['popular', 'Most popular'],
  ['price', 'Price: low to high'],
  ['-price', 'Price: high to low'],
  ['savings', 'Biggest savings'],
  ['name', 'Name A–Z'],
]

export default function ProductBrowser({
  title, filters, query, platforms, selectedPlatforms, onTogglePlatform,
  ordering, onOrdering, availableOnly, onAvailableOnly, onReset, cardActions,
}) {
  const { items, count, hasMore, loading, error, loadMore } = useProducts(filters, {
    ...query,
    ordering,
    available: availableOnly ? 'true' : '',
  })

  return (
    <section className="section" id="browse">
      <div className="section-head">
        <h2>{title}</h2>
        {!loading && !error && <p>{count} product{count === 1 ? '' : 's'}</p>}
      </div>

      <div className="filters">
        <div className="chips" role="group" aria-label="Filter by platform">
          {platforms.map((p) => {
            const on = selectedPlatforms.length === 0 || selectedPlatforms.includes(p.slug)
            return (
              <button
                key={p.slug}
                className={`chip ${on ? 'chip-on' : ''}`}
                style={{ '--platform': p.color }}
                aria-pressed={on}
                onClick={() => onTogglePlatform(p.slug)}
              >
                <span className="dot" />{p.name}
              </button>
            )
          })}
        </div>
        <div className="filter-controls">
          <label className="toggle">
            <input type="checkbox" checked={availableOnly} onChange={(e) => onAvailableOnly(e.target.checked)} />
            <span>In stock only</span>
          </label>
          <select value={ordering} onChange={(e) => onOrdering(e.target.value)} aria-label="Sort products">
            {SORT_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
      </div>

      {error && <p className="inline-error">{error.message}</p>}

      {!error && !loading && items.length === 0 ? (
        <div className="empty">
          <span className="empty-icon" aria-hidden="true">🧺</span>
          <h3>No products match</h3>
          <p>Try a different search, category or platform selection.</p>
          <button className="btn btn-secondary" onClick={onReset}>Clear filters</button>
        </div>
      ) : (
        <div className="grid">
          {items.map((p) => <ProductCard key={p.id} product={p} {...cardActions(p)} />)}
          {loading && <SkeletonCards count={items.length ? 4 : 8} />}
        </div>
      )}

      {hasMore && !loading && (
        <div className="center">
          <button className="btn btn-secondary" onClick={loadMore}>Load more</button>
        </div>
      )}
    </section>
  )
}
