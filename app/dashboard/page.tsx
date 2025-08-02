'use client';

import { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

// Definisikan tipe untuk tugas
type Task = {
  id: number;
  title: string;
  created_at: string;
};

export default function Dashboard() {
  const { session, user, loading } = useAuth();
  
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) {
      router.push('/login');
    }
    if (session) {
      fetchTasks();
    }
  }, [session, loading, router]);

  const fetchTasks = async () => {
    const { data, error } = await supabase
      .from('tasks')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error fetching tasks: ', error);
    } else {
      setTasks(data as Task[]);
    }
  };

  const handleAddTask = async (e: FormEvent) => {
    e.preventDefault();
    if (!user || !newTaskTitle.trim()) return;

    const { error } = await supabase
      .from('tasks')
      .insert({ title: newTaskTitle, user_id: user.id });

    if (error) {
      alert(error.message);
    } else {
      setNewTaskTitle('');
      fetchTasks();
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

  // --- FUNGSI UPLOAD PDF (DISESUAIKAN UNTUK NETLIFY) ---
  const handlePdfUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !user) return;

    alert('Mengunggah PDF... Ini mungkin memakan waktu beberapa saat untuk diproses.');
    const filePath = `${user.id}/${Date.now()}-${file.name}`;

    const { error: uploadError } = await supabase.storage
      .from('schedules')
      .upload(filePath, file);

    if (uploadError) {
      alert('Gagal mengunggah PDF: ' + uploadError.message);
      return;
    }

    // Panggil API menggunakan path Netlify Functions
    const response = await fetch('/.netlify/functions/process_pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filePath }),
    });

    const result = await response.json();
    alert(result.message);
    fetchTasks();
  };

  // --- FUNGSI INPUT NLP (DISESUAIKAN UNTUK NETLIFY) ---
  const handleNlpInput = async (text: string) => {
    if (text.length < 10) return;

    try {
      // Panggil API menggunakan path Netlify Functions
      const response = await fetch('/.netlify/functions/process_nlp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const result = await response.json();

      if (result.title) {
        setNewTaskTitle(result.title);
      }
    } catch (error) {
      console.error("NLP processing error:", error);
    }
  };
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  if (!user) {
    return null;
  }

  return (
    <div style={{ maxWidth: '700px', margin: '50px auto', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Welcome, {user.email}</h1>
        <button onClick={handleSignOut} style={{ padding: '8px 12px', cursor: 'pointer', background: '#f44336', color: 'white', border: 'none', borderRadius: '4px' }}>
          Keluar
        </button>
      </div>

      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Tambah Tugas Baru</h3>
        <form onSubmit={handleAddTask} style={{ display: 'flex', gap: '8px' }}>
          <input 
            type="text" 
            value={newTaskTitle}
            onChange={(e) => {
              setNewTaskTitle(e.target.value);
              handleNlpInput(e.target.value);
            }}
            placeholder="Ketik 'Rapat dengan tim marketing besok jam 2 siang'..."
            style={{ flexGrow: 1, padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
          <button type="submit" style={{ padding: '10px 20px', cursor: 'pointer', background: '#4CAF50', color: 'white', border: 'none', borderRadius: '4px' }}>
            Tambah
          </button>
        </form>
      </div>

      <div style={{ marginBottom: '30px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Atau Unggah Jadwal PDF</h3>
        <input 
          type="file" 
          accept="application/pdf" 
          onChange={handlePdfUpload} 
        />
      </div>

      <div>
        <h2>Daftar Tugas Anda</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {tasks.map((task) => (
            <li key={task.id} style={{ padding: '12px', borderBottom: '1px solid #eee', fontSize: '1.1rem' }}>
              {task.title}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}