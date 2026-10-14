"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";

export interface User {
  id: string;
  email: string;
  display_name: string;
  auto_save_scans: boolean;
  created_at: string;
}

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (email: string, password: string, displayName: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  updateProfile: (data: { display_name?: string; auto_save_scans?: boolean }) => Promise<boolean>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function normalizeUser(raw: unknown): User | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  const u = (obj.user && typeof obj.user === "object" ? obj.user : obj) as Record<string, unknown>;
  if (!u.id || !u.email) return null;

  return {
    id: String(u.id),
    email: String(u.email),
    display_name: String(u.display_name || u.displayName || String(u.email).split("@")[0]),
    auto_save_scans: u.auto_save_scans !== false && u.auto_save_scans !== 0,
    created_at: String(u.created_at || new Date().toISOString()),
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      let res = await fetch("/api/auth/me", {
        method: "GET",
        credentials: "include",
      });

      // Fallback endpoint if /api/auth/me returns 404
      if (res.status === 404) {
        res = await fetch("/api/user/me", {
          method: "GET",
          credentials: "include",
        });
      }

      if (res.ok) {
        const data = await res.json();
        const parsed = normalizeUser(data);
        setUser(parsed);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
      try {
        let res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ email: email.trim(), password }),
        });

        // Fallback endpoint
        if (res.status === 404) {
          res = await fetch("/api/user/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ email: email.trim(), password }),
          });
        }

        if (res.status === 429) {
          let lockMsg = "Tài khoản tạm thời bị khóa do thử quá số lần cho phép. Vui lòng thử lại sau ít phút.";
          try {
            const errData = await res.json();
            if (errData?.detail && typeof errData.detail === "string") {
              lockMsg = errData.detail;
            }
          } catch {}
          return { success: false, error: lockMsg };
        }

        if (!res.ok) {
          let errMsg = "Email hoặc mật khẩu không chính xác.";
          try {
            const errData = await res.json();
            if (errData?.detail) {
              errMsg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
            } else if (errData?.message) {
              errMsg = errData.message;
            }
          } catch {}
          return { success: false, error: errMsg };
        }

        const data = await res.json();
        const parsed = normalizeUser(data);
        if (parsed) {
          setUser(parsed);
          return { success: true };
        } else {
          // Refresh user profile if token cookie was set but user body not in response
          await refreshUser();
          return { success: true };
        }
      } catch {
        return { success: false, error: "Không thể kết nối đến máy chủ. Vui lòng thử lại." };
      }
    },
    [refreshUser]
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      displayName: string
    ): Promise<{ success: boolean; error?: string }> => {
      try {
        let res = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            email: email.trim(),
            password,
            display_name: displayName.trim(),
            displayName: displayName.trim(),
          }),
        });

        // Fallback endpoint
        if (res.status === 404) {
          res = await fetch("/api/user/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
              email: email.trim(),
              password,
              display_name: displayName.trim(),
              displayName: displayName.trim(),
            }),
          });
        }

        if (!res.ok) {
          let errMsg = "Không thể đăng ký tài khoản. Vui lòng kiểm tra lại thông tin.";
          try {
            const errData = await res.json();
            if (errData?.detail) {
              errMsg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
            } else if (errData?.message) {
              errMsg = errData.message;
            }
          } catch {}
          return { success: false, error: errMsg };
        }

        const data = await res.json();
        const parsed = normalizeUser(data);
        if (parsed) {
          setUser(parsed);
          return { success: true };
        } else {
          await refreshUser();
          return { success: true };
        }
      } catch {
        return { success: false, error: "Không thể kết nối đến máy chủ. Vui lòng thử lại." };
      }
    },
    [refreshUser]
  );

  const logout = useCallback(async () => {
    try {
      let res = await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });

      if (res.status === 404) {
        res = await fetch("/api/user/logout", {
          method: "POST",
          credentials: "include",
        });
      }
    } catch {
      // Ignore network errors on logout
    } finally {
      setUser(null);
      // Clean up cached personal scan data from sessionStorage / localStorage
      if (typeof window !== "undefined") {
        try {
          sessionStorage.removeItem("morph_saved_scans_map");
          const keysToRemove: string[] = [];
          for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (
              key &&
              (key.startsWith("morph_scan_") ||
                key.startsWith("morph_user_") ||
                key === "morph_saved_scans_map")
            ) {
              keysToRemove.push(key);
            }
          }
          keysToRemove.forEach((k) => sessionStorage.removeItem(k));
        } catch {}

        // Broadcast custom event so ScanContext and other stores immediately clear memory caches
        window.dispatchEvent(new CustomEvent("morph:auth:logout"));
      }
    }
  }, []);

  const updateProfile = useCallback(
    async (data: { display_name?: string; auto_save_scans?: boolean }): Promise<boolean> => {
      try {
        let res = await fetch("/api/user/profile", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(data),
        });

        if (res.status === 404) {
          res = await fetch("/api/auth/profile", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(data),
          });
        }

        if (res.ok) {
          setUser((prev) => (prev ? { ...prev, ...data } : null));
          return true;
        }
        return false;
      } catch {
        return false;
      }
    },
    []
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        updateProfile,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
