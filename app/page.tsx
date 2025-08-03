// app/page.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './contexts/AuthContext';

export default function HomePage() {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Jangan lakukan apa-apa sampai status autentikasi selesai diperiksa
    if (loading) {
      return;
    }

    if (session) {
      // Jika ada sesi (sudah login), arahkan ke dasbor
      router.push('/dashboard');
    } else {
      // Jika tidak ada sesi (belum login), arahkan ke halaman login
      router.push('/login');
    }
  }, [session, loading, router]);

  // Tampilkan pesan loading sementara pengecekan berlangsung
  return <div>Loading...</div>;
}