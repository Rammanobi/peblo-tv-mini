import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getToken, setToken as persistToken } from '../api/client';
import { getMe, login as loginRequest } from '../api/endpoints';
import type { User } from '../types/api';

interface AuthState {
  user: User | null;
  status: 'loading' | 'authenticated' | 'anonymous';
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthState['status']>('loading');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setStatus('anonymous');
      return;
    }
    getMe()
      .then((u) => {
        setUser(u);
        setStatus('authenticated');
      })
      .catch(() => {
        persistToken(null);
        setStatus('anonymous');
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await loginRequest(email, password);
    persistToken(res.access_token);
    setUser(res.user);
    setStatus('authenticated');
  }, []);

  const logout = useCallback(() => {
    persistToken(null);
    setUser(null);
    setStatus('anonymous');
  }, []);

  const value = useMemo(() => ({ user, status, login, logout }), [user, status, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
