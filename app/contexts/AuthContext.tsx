// app/contexts/AuthContext.tsx
'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { supabase } from '@/lib/supabaseClient'; // Pastikan path ini benar
import { Session, User } from '@supabase/supabase-js';

// Definisikan tipe untuk nilai context
type AuthContextType = {
  session: Session | null;
  user: User | null;
  loading: boolean;
};

// Buat Context dengan nilai default
const AuthContext = createContext<AuthContextType>({
  session: null,
  user: null,
  loading: true,
});

// Buat Provider Component
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Ambil sesi awal saat komponen dimuat
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Dengarkan perubahan status autentikasi (login, logout)
    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    // Hentikan listener saat komponen tidak lagi digunakan
    return () => {
      authListener?.subscription.unsubscribe();
    };
  }, []);

  const value = {
    session,
    user,
    loading,
  };

  // Sediakan nilai context ke komponen anak
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Buat Custom Hook untuk menggunakan context dengan mudah
export const useAuth = () => {
  return useContext(AuthContext);
};