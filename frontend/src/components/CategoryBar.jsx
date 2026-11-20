export default function CategoryBar({ categories, active, onSelect }) {
  return (
    <nav className="categories" aria-label="Categories">
      <button className={`category ${!active ? 'active' : ''}`} onClick={() => onSelect('')}>
        <span className="category-icon">✨</span>
        <span>All</span>
      </button>
      {categories.map((c) => (
        <button
          key={c.slug}
          className={`category ${active === c.slug ? 'active' : ''}`}
          data-category={c.slug}
          onClick={() => onSelect(active === c.slug ? '' : c.slug)}
        >
          <span className="category-icon">{c.icon}</span>
          <span>{c.name}</span>
        </button>
      ))}
    </nav>
  )
}
