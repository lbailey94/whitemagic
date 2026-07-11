/**
 * Login Modal — Simple user authentication
 *
 * Allows users to create or switch accounts for per-user data isolation.
 */

"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";

export function LoginModal({ onClose }: { onClose?: () => void }) {
  const { login, users, switchUser, logout, user } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [mode, setMode] = useState<"login" | "switch">("login");
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) {
      setError("Name and email are required");
      return;
    }

    try {
      await login(name.trim(), email.trim());
      setError(null);
      onClose?.();
    } catch (err) {
      setError("Failed to create account");
    }
  };

  if (user) {
    return (
      <div className="p-6 rounded-lg bg-gray-900 border border-gray-700 space-y-4">
        <h3 className="text-lg font-bold text-white">Account</h3>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-white font-medium">{user.name}</p>
            <p className="text-gray-400 text-sm">{user.email}</p>
          </div>
        </div>

        {users.length > 1 && (
          <div className="space-y-2">
            <p className="text-sm text-gray-400">Switch Account</p>
            <div className="space-y-1">
              {users.filter(u => u.id !== user.id).map(u => (
                <button
                  key={u.id}
                  onClick={() => switchUser(u.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded bg-gray-800 hover:bg-gray-700 text-left transition-colors"
                >
                  <div className="w-6 h-6 rounded-full bg-gray-600 flex items-center justify-center text-white text-xs">
                    {u.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm text-gray-300">{u.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={logout}
          className="w-full px-4 py-2 rounded bg-red-600/20 hover:bg-red-600/30 text-red-400 text-sm transition-colors"
        >
          Logout
        </button>

        {onClose && (
          <button
            onClick={onClose}
            className="w-full px-4 py-2 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
          >
            Close
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="p-6 rounded-lg bg-gray-900 border border-gray-700 space-y-4">
      <h3 className="text-lg font-bold text-white">
        {mode === "login" ? "Create Account" : "Switch Account"}
      </h3>

      {users.length > 0 && mode === "login" && (
        <div className="space-y-2">
          <p className="text-sm text-gray-400">Existing Accounts</p>
          <div className="space-y-1">
            {users.map(u => (
              <button
                key={u.id}
                onClick={() => switchUser(u.id)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded bg-gray-800 hover:bg-gray-700 text-left transition-colors"
              >
                <div className="w-6 h-6 rounded-full bg-gray-600 flex items-center justify-center text-white text-xs">
                  {u.name.charAt(0).toUpperCase()}
                </div>
                <span className="text-sm text-gray-300">{u.name}</span>
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 text-center">or create a new account</p>
        </div>
      )}

      <form onSubmit={handleLogin} className="space-y-3">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
            placeholder="Your name"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
            placeholder="you@example.com"
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          className="w-full px-4 py-2 rounded bg-purple-600 hover:bg-purple-700 text-white font-medium transition-colors"
        >
          {mode === "login" ? "Create Account" : "Login"}
        </button>
      </form>
    </div>
  );
}
