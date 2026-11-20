export default function Header({ locations, location, onLocationChange, search, onSearch, cartCount, onOpenCart, onHome }) {
  return (
    <header className="header">
      <div className="header-inner">
        <button className="logo" onClick={onHome} aria-label="Cartzy home">
          <span className="logo-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32"><path d="M6 8h3l2.6 12.2a2 2 0 0 0 2 1.6h9.2a2 2 0 0 0 1.9-1.4L27 12H11" /><circle cx="14" cy="26" r="1.8" /><circle cx="23" cy="26" r="1.8" /></svg>
          </span>
          <span className="logo-text">C<span className="logo-a">A</span><span className="logo-r">R</span>TZY</span>
        </button>

        <label className="location-picker">
          <span className="location-label">Delivering to</span>
          <span className="location-select-wrap">
            <span aria-hidden="true">📍</span>
            <select value={location || ''} onChange={(e) => onLocationChange(e.target.value)} aria-label="Delivery location">
              {locations.map((l) => (
                <option key={l.slug} value={l.slug}>{l.name}, {l.city}</option>
              ))}
            </select>
          </span>
        </label>

        <div className="search">
          <span className="search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            placeholder="Search salt, toothpaste, Amul butter…"
            aria-label="Search products"
          />
        </div>

        <button className="cart-button" onClick={onOpenCart}>
          <span aria-hidden="true">🧾</span>
          <span className="cart-button-text">My list</span>
          {cartCount > 0 && <span className="cart-badge" key={cartCount}>{cartCount}</span>}
        </button>
      </div>
    </header>
  )
}
