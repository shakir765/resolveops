import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

const STORAGE_KEY = "resolveops_portal_user_id";

interface UserContextValue {
  userId: string | null;
  setUserId: (id: string) => void;
  clearUser: () => void;
}

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setUserIdState] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY);
  });

  const value = useMemo(
    () => ({
      userId,
      setUserId: (id: string) => {
        const trimmed = id.trim();
        if (!trimmed) return;
        localStorage.setItem(STORAGE_KEY, trimmed);
        setUserIdState(trimmed);
      },
      clearUser: () => {
        localStorage.removeItem(STORAGE_KEY);
        setUserIdState(null);
      },
    }),
    [userId],
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within UserProvider");
  return ctx;
}
