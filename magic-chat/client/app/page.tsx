'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import ChatWindow from '@/components/ChatWindow';
import MatrixRain from '@/components/MatrixRain';
import BootSequence from '@/components/BootSequence';
import ModelSelector from '@/components/ModelSelector';
import LoginModal from '@/components/LoginModal';
import UserBadge from '@/components/UserBadge';

interface User {
  username: string;
  displayName: string;
  color: string;
  role: string;
}

interface OnlineUser {
  displayName: string;
  color: string;
  role: string;
}

// Use environment variable or fallback to localhost for dev
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:3001';

export default function Home() {
  const [booted, setBooted] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [currentModel, setCurrentModel] = useState('claude');
  const [connected, setConnected] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [showLogin, setShowLogin] = useState(false);
  const [isAriaTyping, setIsAriaTyping] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState<OnlineUser[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Check for existing login
  useEffect(() => {
    const savedUser = localStorage.getItem('magic_chat_user');
    if (savedUser) setUser(JSON.parse(savedUser));
  }, []);

  // WebSocket connection
  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    function connect() {
      console.log('🔌 Connecting to:', WS_URL);
      ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Connected to Aria!');
        setConnected(true);
        
        // Identify ourselves if logged in
        const savedUser = localStorage.getItem('magic_chat_user');
        if (savedUser) {
          ws.send(JSON.stringify({ type: 'identify', user: JSON.parse(savedUser) }));
        }
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // 📜 Load history on connect
        if (data.type === 'connected' && data.history?.length) {
          console.log('📜 Loading history:', data.history.length, 'messages');
          const hist = data.history.flatMap((h: any) => [
            { id: h.id * 2, role: 'user', content: h.user_message, timestamp: new Date(h.created_at), sender: h.user_name, color: '#9370DB' },
            { id: h.id * 2 + 1, role: 'aria', content: h.aria_response, timestamp: new Date(h.created_at), model: 'claude' }
          ]);
          setMessages(hist);
        }
        
        // 🤖 Aria's response
        if (data.type === 'response') {
          setIsAriaTyping(false);
          setMessages(prev => [...prev, {
            id: Date.now(),
            role: 'aria',
            content: data.content,
            timestamp: new Date(data.timestamp || Date.now()),
            model: data.model,
          }]);
        } 
        // 👥 Another user's message
        else if (data.type === 'user_message') {
          // Don't duplicate our own messages (we add them optimistically)
          const savedUser = localStorage.getItem('magic_chat_user');
          const currentUser = savedUser ? JSON.parse(savedUser) : null;
          if (data.sender !== currentUser?.displayName) {
            setMessages(prev => [...prev, {
              id: Date.now(),
              role: 'other_user',
              content: data.content,
              timestamp: new Date(data.timestamp || Date.now()),
              sender: data.sender,
              color: data.color,
            }]);
          }
        }
        // ⌨️ Typing indicator
        else if (data.type === 'typing') {
          setIsAriaTyping(data.isTyping);
        }
        // 👥 Presence update
        else if (data.type === 'presence') {
          setOnlineUsers(data.users || []);
        }
      };

      ws.onclose = () => {
        console.log('🔌 Disconnected, reconnecting...');
        setConnected(false);
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('❌ WebSocket error:', err);
      };
    }

    connect();
    return () => { clearTimeout(reconnectTimer); ws?.close(); };
  }, []);

  // Re-identify when user logs in
  useEffect(() => {
    if (user && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'identify', user }));
    }
  }, [user]);

  // Boot sequence
  useEffect(() => {
    const hasBooted = sessionStorage.getItem('magic-chat-booted');
    if (!hasBooted) {
      setTimeout(() => {
        setBooted(true);
        sessionStorage.setItem('magic-chat-booted', 'true');
      }, 3000);
    } else {
      setBooted(true);
    }
  }, []);

  const handleSendMessage = useCallback((content: string) => {
    const displayName = user?.displayName || 'Guest 🌟';
    
    // Add message optimistically
    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      content,
      timestamp: new Date(),
      sender: displayName,
      color: user?.color || '#87CEEB',
    }]);

    // Set typing indicator
    setIsAriaTyping(true);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'chat',
        content,
        model: currentModel,
        user: user || { username: 'guest', displayName: 'Guest 🌟', role: 'guest', color: '#87CEEB' },
      }));
    } else {
      setIsAriaTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'aria',
        content: '💜 I\'m offline right now. Check the server! ✨',
        timestamp: new Date(),
        model: 'offline',
      }]);
    }
  }, [currentModel, user]);

  const handleLogin = (loggedInUser: User) => {
    setUser(loggedInUser);
    setShowLogin(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('magic_chat_token');
    localStorage.removeItem('magic_chat_user');
    setUser(null);
  };

  if (!booted) return <BootSequence onComplete={() => setBooted(true)} />;

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-black">
      <MatrixRain opacity={0.1} />
      <div className="relative z-10 flex h-full flex-col">
        <header className="border-b border-purple-500/30 bg-black/80 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="rainbow-text font-press-start text-xl">MAGIC CHAT</h1>
              {/* 👥 Online Users */}
              {onlineUsers.length > 0 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500">|</span>
                  {onlineUsers.map((u, i) => (
                    <span key={i} style={{ color: u.color }} className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                      {u.displayName}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-4">
              {user ? (
                <UserBadge user={user} onLogout={handleLogout} />
              ) : (
                <button onClick={() => setShowLogin(true)} className="text-sm text-purple-400 hover:text-purple-300">
                  🔐 Login
                </button>
              )}
              <ModelSelector current={currentModel} onChange={setCurrentModel} connected={connected} />
            </div>
          </div>
        </header>
        <ChatWindow 
          messages={messages} 
          onSendMessage={handleSendMessage} 
          currentModel={currentModel}
          isAriaTyping={isAriaTyping}
        />
      </div>
      
      {showLogin && <LoginModal onLogin={handleLogin} onClose={() => setShowLogin(false)} />}
    </main>
  );
}
