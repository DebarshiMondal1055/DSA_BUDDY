/**
 * API service for DSA Buddy backend communication.
 * Automatically tries local proxy first, then falls back to direct http://localhost:8000.
 */

const BASE_URL = '' // Vite proxy handles /similar, /health, /ladder
const BACKUP_URL = 'http://localhost:8000'

async function request(path, options = {}) {
  // First attempt via relative URL (Vite dev proxy)
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    })
    if (res.ok) {
      return await res.json()
    }
  } catch (err) {
    console.warn(`Relative fetch to ${path} failed, attempting direct to ${BACKUP_URL}${path}...`, err)
  }

  // Fallback to direct backend address
  const directRes = await fetch(`${BACKUP_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  if (!directRes.ok) {
    let errMsg = `Request failed with status ${directRes.status}`
    try {
      const errData = await directRes.json()
      if (errData?.detail) errMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail)
    } catch {
      // Ignored
    }
    throw new Error(errMsg)
  }

  return await directRes.json()
}

/**
 * Check backend health
 */
export async function checkHealth() {
  try {
    const res = await request('/health')
    return res?.status === 'ok'
  } catch {
    return false
  }
}

/**
 * Search similar problems via /similar
 * @param {Object} queryObj
 * @param {string} queryObj.query Problem URL or statement
 * @param {string|null} [queryObj.solution_code] Optional AC code
 * @param {number} [queryObj.k] Number of problems
 * @param {'both'|'method'|'concept'} [queryObj.mode] Mode
 * @param {number} [queryObj.per_platform_min] Min per platform
 * @param {string|null} [queryObj.platform] Target platform
 */
export async function searchSimilar(queryObj) {
  const data = await request('/similar', {
    method: 'POST',
    body: JSON.stringify({
      query: queryObj.query,
      solution_code: queryObj.solution_code || null,
      k: queryObj.k ?? 12,
      mode: queryObj.mode ?? 'both',
      per_platform_min: queryObj.per_platform_min ?? 3,
      platform: queryObj.platform || null,
    }),
  })

  // Backend returns: { data: { source: {...}, results: [...] }, message: "..." }
  return data?.data || data
}

/**
 * Fetch practice ladder for a method key
 */
export async function fetchLadder(methodKey, around = null, n = 12) {
  const params = new URLSearchParams({ method_key: methodKey, n: String(n) })
  if (around !== null) params.append('around', String(around))
  return await request(`/ladder?${params.toString()}`)
}
