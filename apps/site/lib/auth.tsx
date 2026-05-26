/**
 * Auth Provider — Simple browser-based authentication
 *
 * Provides user identity for per-user data isolation.
 * Uses localStorage for persistence (no server required).
 *
 * For production: integrate with a proper auth provider (Clerk, Auth0, etc.)
 */

"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  createdAt: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (name: string, email: string) => Promise<User>;
  logout: () => void;
  switchUser: (userId: string) => void;
  users: User[];
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

// Storage keys
const USERS_KEY = "whitemagic_users";
const CURRENT_USER_KEY = "whitemagic_current_user";

function getUsers(): User[] {
  try {
    const data = localStorage.getItem(USERS_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

function saveUsers(users: User[]): void {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function getCurrentUserId(): string | null {
  return localStorage.getItem(CURRENT_USER_KEY);
}

function setCurrentUserId(id: string | null): void {
  if (id) {
    localStorage.setItem(CURRENT_USER_KEY, id);
  } else {
    localStorage.removeItem(CURRENT_USER_KEY);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load current user on mount
  useEffect(() => {
    const allUsers = getUsers();
    setUsers(allUsers);

    const currentId = getCurrentUserId();
    if (currentId) {
      const found = allUsers.find(u => u.id === currentId);
      if (found) {
        setUser(found);
      }
    }

    setIsLoading(false);
  }, []);

  const login = useCallback(async (name: string, email: string): Promise<User> => {
    const allUsers = getUsers();

    // Check if user exists by email
    let existing = allUsers.find(u => u.email === email);
    if (existing) {
      setUser(existing);
      setCurrentUserId(existing.id);
      return existing;
    }

    // Create new user
    const newUser: User = {
      id: `user_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      name,
      email,
      createdAt: new Date().toISOString(),
    };

    const updated = [...allUsers, newUser];
    saveUsers(updated);
    setUsers(updated);
    setUser(newUser);
    setCurrentUserId(newUser.id);

    return newUser;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setCurrentUserId(null);
  }, []);

  const switchUser = useCallback((userId: string) => {
    const allUsers = getUsers();
    const found = allUsers.find(u => u.id === userId);
    if (found) {
      setUser(found);
      setCurrentUserId(found.id);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, switchUser, users }}>
      {children}
    </AuthContext.Provider>
  );
}

// Get user-specific OPFS path
export function getUserOPFSPath(userId: string): string {
  return `whitemagic_${userId}.db`;
}
