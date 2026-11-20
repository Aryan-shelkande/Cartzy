// Tiny dependency-free confetti burst on a temporary canvas.
const COLORS = ['#E8278F', '#FFC233', '#6A1B9A', '#B0136B', '#FFD97A', '#F7A8D0']

export function celebrate() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  const canvas = document.createElement('canvas')
  canvas.className = 'confetti-canvas'
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  document.body.appendChild(canvas)
  const ctx = canvas.getContext('2d')

  const pieces = Array.from({ length: 110 }, (_, i) => {
    const fromLeft = i % 2 === 0
    return {
      x: fromLeft ? 0 : canvas.width,
      y: canvas.height * 0.75,
      vx: (fromLeft ? 1 : -1) * (4 + Math.random() * 7),
      vy: -(9 + Math.random() * 8),
      size: 5 + Math.random() * 6,
      spin: Math.random() * Math.PI,
      color: COLORS[i % COLORS.length],
    }
  })

  const start = performance.now()
  function frame(now) {
    const t = now - start
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.globalAlpha = Math.max(0, 1 - t / 1800)
    for (const p of pieces) {
      p.vy += 0.32
      p.vx *= 0.99
      p.x += p.vx
      p.y += p.vy
      p.spin += 0.15
      ctx.save()
      ctx.translate(p.x, p.y)
      ctx.rotate(p.spin)
      ctx.fillStyle = p.color
      ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2)
      ctx.restore()
    }
    if (t < 1800) requestAnimationFrame(frame)
    else canvas.remove()
  }
  requestAnimationFrame(frame)
}
