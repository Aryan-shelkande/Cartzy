import { useState } from 'react'

/** Product photo, or the product's emoji tile when there is no photo or it fails to load. */
export default function ProductImage({ product, size = 'md' }) {
  const [failedSrc, setFailedSrc] = useState(null)
  const category = product.category?.slug ?? product.category // full category object or just its slug
  const showImage = product.image_url && failedSrc !== product.image_url

  return (
    <div className={`product-image product-image-${size}`} data-category={category}>
      {showImage
        ? <img src={product.image_url} alt={product.name} loading="lazy" decoding="async" onError={() => setFailedSrc(product.image_url)} />
        : <span aria-hidden="true">{product.emoji || product.category?.icon || '🛒'}</span>}
    </div>
  )
}
