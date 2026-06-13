import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api } from "../api/client";
import type { User } from "../types/api";

type LoginPayload = {
  identifier: string;
  password: string;
};

type RegisterPayload = {
  email: string;
  username?: string;
  nickname?: string;
  password: string;
};

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadCurrentUser() {
    await api.ensureCsrf();
    return api.get<User>("/auth/me/");
  }

  useEffect(() => {
    let mounted = true;

    api
      .ensureCsrf()
      .then(() => api.get<User>("/auth/me/"))
      .then((currentUser) => {
        if (mounted) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        if (mounted) {
          setUser(null);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (payload) => {
        try {
          const loggedInUser = await api.post<User>("/auth/login/", payload);
          setUser(loggedInUser);
        } catch (error) {
          if (!(error instanceof TypeError)) {
            throw error;
          }
          const currentUser = await loadCurrentUser();
          setUser(currentUser);
        }
      },
      register: async (payload) => {
        await api.post<User>("/auth/register/", payload);
        const loggedInUser = await api.post<User>("/auth/login/", {
          identifier: payload.email,
          password: payload.password
        });
        setUser(loggedInUser);
      },
      logout: async () => {
        await api.post<null>("/auth/logout/");
        setUser(null);
      }
    }),
    [loading, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return value;
}
