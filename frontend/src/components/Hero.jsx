const QUICK_ADDS = ['Salt', 'Sugar', 'Soap', 'Toothpaste', 'Toothbrush', 'Milk', 'Atta', 'Tea']

export default function Hero({ platformCount, locationName, onQuickSearch }) {
  return (
    <section className="hero">
      <div className="hero-glow" aria-hidden="true" />
      <div className="hero-text">
        <span className="eyebrow">📍 Delivering in {locationName}</span>
        <h1>Add everything you need. <em>Compare your entire cart.</em> Shop where you save the most.</h1>
        <p>
          Cartzy adds up your whole list on {platformCount} apps, including delivery, handling and platform fees
          and discounts, so you see the amount you would actually pay.
        </p>
        <div className="quick-adds" aria-label="Start your list">
          {QUICK_ADDS.map((term) => (
            <button key={term} className="quick-add" onClick={() => onQuickSearch(term)}>{term}</button>
          ))}
        </div>
      </div>
      <ol className="hero-steps">
        <li><b>1</b><span>Pick your delivery location</span></li>
        <li><b>2</b><span>Add items and choose brands</span></li>
        <li><b>3</b><span>Compare your whole cart</span></li>
      </ol>
    </section>
  )
}
