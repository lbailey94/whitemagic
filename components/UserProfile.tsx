/**
 * User Profile — Shows current user and login/logout actions
 */

"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { LoginModal } from "@/components/LoginModal";

export function UserProfile() {
  const { user } = useAuth();
  const [showModal, setShowModal] = useState(false);

  if (!user) {
    return (
      <>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
        >
          <div className="w-5 h-5 rounded-full bg-purple-600 flex items-center justify-center text-white text-xs">
            ?
          </div>
          <span>Sign In</span>
        </button>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="w-full max-w-md mx-4">
              <LoginModal onClose={() => setShowModal(false)} />
            </div>
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="flex items-center gap-2 px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
      >
        <div className="w-5 h-5 rounded-full bg-purple-600 flex items-center justify-center text-white text-xs">
          {user.name.charAt(0).toUpperCase()}
        </div>
        <span>{user.name}</span>
      </button>
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="w-full max-w-md mx-4">
            <LoginModal onClose={() => setShowModal(false)} />
          </div>
        </div>
      )}
    </>
  );
}
