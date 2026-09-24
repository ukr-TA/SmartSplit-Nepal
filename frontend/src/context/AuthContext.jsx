import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { TOKEN_KEY } from '../api/client'
import { authApi } from '../api/services'

const AuthContext = createContext(null)

function readToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function writeToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage unavailable (private mode) - session lasts until refresh */
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // "checking" only when a saved token needs to be verified on first load
  const [checking, setChecking] = useState(() => Boolean(readToken()))

  const applySession = useCallback(({ token, user: profile }) => {
    writeToken(token)
    setUser(profile)
  }, [])

  const clearSession = useCallback(() => {
    writeToken(null)
    setUser(null)
  }, [])

  // Restore the session on page load
  useEffect(() => {
    if (!readToken()) return
    authApi
      .profile()
      .then(setUser)
      .catch(() => clearSession())
      .finally(() => setChecking(false))
  }, [clearSession])

  // Any 401 from the API logs the user out
  useEffect(() => {
    const onUnauthorized = () => clearSession()
    window.addEventListener('smartsplit:unauthorized', onUnauthorized)
    return () => window.removeEventListener('smartsplit:unauthorized', onUnauthorized)
  }, [clearSession])

  const value = useMemo(
    () => ({
      user,
      checking,
      isAuthenticated: Boolean(user),
      login: async (identifier, password) => applySession(await authApi.login(identifier, password)),
      register: async (body) => applySession(await authApi.register(body)),
      logout: async () => {
        try {
          await authApi.logout()
        } finally {
          clearSession()
        }
      },
      setUser,
      applySession,
    }),
    [user, checking, applySession, clearSession],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
