// app/signup/page.tsx
'use client';

import { useState } from 'react';
import { supabase } from '@/lib/supabaseClient'; // Pastikan path ini benar
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function SignUpPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const router = useRouter();

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    });

    if (error) {
      setMessage('Gagal mendaftar: ' + error.message);
    } else if (data.user) {
      // Periksa apakah email perlu dikonfirmasi
      if (data.user.identities && data.user.identities.length === 0) {
         setMessage('Pendaftaran berhasil! Silakan cek email Anda untuk verifikasi.');
      } else {
         setMessage('Pendaftaran berhasil! Anda akan diarahkan ke halaman login.');
         setTimeout(() => {
            router.push('/login');
         }, 3000); // Arahkan setelah 3 detik
      }
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: '400px', margin: '50px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
      <h2>Buat Akun Baru</h2>
      <form onSubmit={handleSignUp}>
        <div>
          <label htmlFor="email">Email:</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', padding: '8px', marginBottom: '10px' }}
          />
        </div>
        <div>
          <label htmlFor="password">Password:</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: '100%', padding: '8px', marginBottom: '20px' }}
          />
        </div>
        <button type="submit" disabled={loading} style={{ width: '100%', padding: '10px', cursor: 'pointer' }}>
          {loading ? 'Mendaftar...' : 'Daftar'}
        </button>
      </form>
      {message && <p style={{ marginTop: '15px', color: 'blue' }}>{message}</p>}
      <p style={{ marginTop: '20px', textAlign: 'center' }}>
        Sudah punya akun? <Link href="/login">Masuk di sini</Link>
      </p>
    </div>
  );
}