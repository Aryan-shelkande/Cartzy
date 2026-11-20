const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function request(path, { method = 'GET', body, params } = {}) {
  const url = new URL(BASE_URL + path)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
  })

  let res
  try {
    res = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('Cannot reach the Cartzy server. Is the backend running?')
  }

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const error = new Error(data?.error?.message || `Request failed (${res.status})`)
    error.status = res.status
    error.details = data?.error?.details
    throw error
  }
  return data
}

// Shared filters (location slug + platform slugs) sent with every price query.
const scope = ({ location, platforms }) => ({ location, platforms: platforms?.join(',') })

export const api = {
  locations: () => request('/locations/'),
  categories: () => request('/categories/'),
  platforms: () => request('/platforms/'),
  products: (filters, query = {}) =>
    request('/products/', { params: { ...scope(filters), ...query } }),
  compareProduct: (id, filters) =>
    request(`/products/${id}/compare/`, { params: scope(filters) }),

  createCart: () => request('/carts/', { method: 'POST' }),
  getCart: (id) => request(`/carts/${id}/`),
  addItem: (id, productId, quantity = 1) =>
    request(`/carts/${id}/items/`, { method: 'POST', body: { product_id: productId, quantity } }),
  // changes: { quantity?, accept_alternatives?, product_id? (switch brand) }
  updateItem: (id, productId, changes) =>
    request(`/carts/${id}/items/${productId}/`, { method: 'PATCH', body: changes }),
  removeItem: (id, productId) =>
    request(`/carts/${id}/items/${productId}/`, { method: 'DELETE' }),
  clearCart: (id) => request(`/carts/${id}/items/`, { method: 'DELETE' }),
  compareCart: (id, filters) =>
    request(`/carts/${id}/compare/`, { params: scope(filters) }),
}
