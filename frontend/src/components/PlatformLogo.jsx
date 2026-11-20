import { useState } from 'react'

/** Platform logo on a white tile; falls back to a coloured initial if the image is missing. */
export default function PlatformLogo({ platform, size = 'md' }) {
  const [failedSrc, setFailedSrc] = useState(null)
  const showImage = platform.logo_url && failedSrc !== platform.logo_url

  return (
    <span className={`platform-logo platform-logo-${size}`} style={{ '--platform': platform.color }} title={platform.name}>
      {showImage
        ? <img src={platform.logo_url} alt={platform.name} loading="lazy" onError={() => setFailedSrc(platform.logo_url)} />
        : <span className="platform-initial" aria-label={platform.name}>{platform.name.slice(0, 1)}</span>}
    </span>
  )
}
