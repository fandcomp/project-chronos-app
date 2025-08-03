'use client';

import { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

// Definisikan tipe untuk tugas, termasuk google_calendar_event_id
type Task = {
  id: number;
  title: string;
  created_at: string;
  google_calendar_event_id: string | null;
};

export default function Dashboard() {
  const { session, user, loading } = useAuth();
  
  const [tasks, setTasks] = useState<Task[]>([]);
  const [command, setCommand] = useState('');
  const [isAgentLoading, setIsAgentLoading] = useState(false);
  const [agentResponse, setAgentResponse] = useState('');

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

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

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

    const response = await fetch('/.netlify/functions/process_pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filePath }),
    });

    const result = await response.json();
    alert(result.message);
    fetchTasks();
  };
  
  const handleGoogleConnect = async () => {
    const response = await fetch('/.netlify/functions/google_auth_url');
    const data = await response.json();
    if (data.auth_url) {
        window.location.href = data.auth_url;
    } else {
        alert("Gagal mendapatkan URL otentikasi.");
    }
  };

  const handleDelete = async (taskId: number, googleEventId: string | null) => {
    if (!user || !confirm("Apakah Anda yakin ingin menghapus tugas ini?")) {
      return;
    }

    try {
      const response = await fetch('/.netlify/functions/delete_task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          google_event_id: googleEventId,
          user_id: user.id
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Gagal menghapus tugas.');
      }
      
      const result = await response.json();
      alert(result.message);
      fetchTasks();
    } catch (error: any) {
      console.error(error);
      alert(`Terjadi kesalahan: ${error.message}`);
    }
  };

  const handleUpdate = (task: Task) => {
    alert(`Fitur "Ubah" untuk tugas "${task.title}" belum diimplementasikan sepenuhnya.`);
    // Di sini Anda akan membuka modal/form untuk mengubah data 'task'
  };

  const handleAgentQuery = async (e: FormEvent) => {
    e.preventDefault();
    if (!command.trim() || !user) return;

    setIsAgentLoading(true);
    setAgentResponse('');

    try {
      const response = await fetch('/.netlify/functions/agent_handler', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: command,
          user_id: user.id
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Agent gagal merespons.');
      }

      const result = await response.json();
      setAgentResponse(result.response);
      
      fetchTasks();

    } catch (error: any) {
      console.error(error);
      setAgentResponse(`Terjadi kesalahan: ${error.message}`);
    } finally {
      setIsAgentLoading(false);
      setCommand('');
    }
  };
  
  if (loading) return <div>Loading...</div>;
  if (!user) return null;

  return (
    <div style={{ maxWidth: '700px', margin: '50px auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Welcome, {user.email}</h1>
        <button onClick={handleSignOut} style={{ padding: '8px 12px', cursor: 'pointer', background: '#dc3545', color: 'white', border: 'none', borderRadius: '4px' }}>
          Keluar
        </button>
      </div>

      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px', background: '#f9f9f9' }}>
        <h3>Chronos Command Bar 🤖</h3>
        <p style={{ fontSize: '0.9em', color: '#666', marginTop: 0 }}>Berikan perintah dalam bahasa alami kepada AI Agent Anda.</p>
        <form onSubmit={handleAgentQuery} style={{ display: 'flex', gap: '8px' }}>
          <input 
            type="text" 
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Contoh: Tambah tugas 'Rapat tim' besok jam 10 pagi"
            style={{ flexGrow: 1, padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
            disabled={isAgentLoading}
          />
          <button type="submit" style={{ padding: '10px 20px', cursor: 'pointer', background: '#5e35b1', color: 'white', border: 'none', borderRadius: '4px' }} disabled={isAgentLoading}>
            {isAgentLoading ? 'Thinking...' : 'Kirim'}
          </button>
        </form>
        {agentResponse && (
          <div style={{ marginTop: '10px', padding: '10px', background: '#e9e9e9', borderRadius: '4px', whiteSpace: 'pre-wrap' }}>
            <strong>Chronos:</strong> {agentResponse}
          </div>
        )}
      </div>
      
      <div style={{ marginBottom: '30px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
          <h3>Pengaturan & Integrasi</h3>
          <p style={{ fontSize: '0.9em', color: '#666', marginTop: 0 }}>Unggah jadwal dari file PDF atau hubungkan kalender Anda.</p>
          <div style={{marginTop: '10px'}}>
            <label htmlFor="pdf-upload" style={{marginRight: '15px'}}>Unggah PDF:</label>
            <input id="pdf-upload" type="file" accept="application/pdf" onChange={handlePdfUpload} />
          </div>
          <button 
              onClick={handleGoogleConnect} 
              style={{ padding: '10px 20px', cursor: 'pointer', background: '#4285F4', color: 'white', border: 'none', borderRadius: '4px', marginTop: '15px' }}>
              Hubungkan Google Calendar
          </button>
      </div>

      <div style={{ marginTop: '30px' }}>
        <h2>Daftar Tugas Anda</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {tasks.length > 0 ? tasks.map((task) => (
            <li key={task.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', borderBottom: '1px solid #eee', fontSize: '1.1rem' }}>
              <span>{task.title}</span>
              <div>
                <button onClick={() => handleUpdate(task)} style={{ marginRight: '10px', padding: '5px 10px', background: '#ffc107', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                  Ubah
                </button>
                <button onClick={() => handleDelete(task.id, task.google_calendar_event_id)} style={{ padding: '5px 10px', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                  Hapus
                </button>
              </div>
            </li>
          )) : <p>Belum ada tugas.</p>}
        </ul>
      </div>
    </div>
  );
}