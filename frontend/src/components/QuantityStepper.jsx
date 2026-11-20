export default function QuantityStepper({ quantity, onChange, small }) {
  return (
    <div className={`stepper ${small ? 'stepper-sm' : ''}`}>
      <button onClick={() => onChange(quantity - 1)} aria-label="Decrease quantity">−</button>
      <span>{quantity}</span>
      <button onClick={() => onChange(quantity + 1)} disabled={quantity >= 99} aria-label="Increase quantity">+</button>
    </div>
  )
}
