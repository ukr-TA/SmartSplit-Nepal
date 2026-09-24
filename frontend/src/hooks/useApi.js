import { useCallback, useEffect, useRef, useState } from 'react'
import { getErrorMessage } from '../api/client'

/**
 * Load data from the API.
 *   const { data, loading, error, reload } = useApi(() => groupApi.get(id), [id])
 */
export function useApi(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const run = useCallback((silent = false) => {
    if (!silent) setState((s) => ({ ...s, loading: true, error: null }))
    return fetcherRef
      .current()
      .then((data) => {
        setState({ data, loading: false, error: null })
        return data
      })
      .catch((err) => {
        setState((s) => ({ ...s, loading: false, error: getErrorMessage(err), status: err.response?.status }))
      })
  }, [])

  useEffect(() => {
    let active = true
    fetcherRef
      .current()
      .then((data) => active && setState({ data, loading: false, error: null }))
      .catch((err) => active && setState({ data: null, loading: false, error: getErrorMessage(err), status: err.response?.status }))
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { ...state, reload: run, setData: (data) => setState((s) => ({ ...s, data })) }
}
