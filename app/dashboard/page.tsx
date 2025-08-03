'use client';

import { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

// Impor untuk FullCalendar
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import dayGridPlugin from '@fullcalendar/daygrid';

// Definisikan tipe event untuk FullCalendar
interface CalendarEvent {
  title: string;
  start: string;
  end: string;
}

export default function Dashboard() {
  const { session, user, loading } = useAuth();
  
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [command, setCommand] = useState('');
  const [isAgentLoading, setIsAgentLoading] = useState(false);
  const [agentResponse, setAgentResponse] = useState('');

  const router = useRouter();

  const fetchWeeklyTasks = async () => {
    if (!user) return;
    
    const today = new Date();
    const nextSevenDays = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);

    const { data, error } = await supabase
      .from('tasks')
      .select('title, start_time, end_time')
      .eq('user_id', user.id)
      .gte('start_time', today.toISOString())
      .lte('start_time', nextSevenDays.toISOString())
      .order('start_time', { ascending: true });

    if (error) {
      console.error('Error fetching weekly tasks: ', error);
    } else if (data) {
      const formattedEvents = data
        .filter(task => task.start_time && task.end_time)
        .map(task => ({
          title: task.title,
          start: task.start_time!,
          end: task.end_time!,
        }));
      setEvents(formattedEvents);
    }
  };

  useEffect(() => {
    if (!loading && !session) {
      router.push('/login');
    }
    if (session) {
      fetchWeeklyTasks();
    }
  }, [session, loading, router]);
  
  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

  const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !user) return;

    alert('Mengunggah file untuk dianalisis AI... Ini mungkin memakan waktu.');
    const filePath = `${user.id}/${Date.now()}-${file.name}`;

    const { error: uploadError } = await supabase.storage
      .from('schedules')
      .upload(filePath, file);

    if (uploadError) {
      alert('Gagal mengunggah file: ' + uploadError.message);
      return;
    }

    const response = await fetch('/.netlify/functions/api/analyze_schedule_file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
          filePath: filePath,
          user_id: user.id
      }),
    });

    const result = await response.json();
    alert(result.message);
    fetchWeeklyTasks();
  };

  const handleGoogleConnect = async () => {
    const response = await fetch('/.netlify/functions/api/google_auth_url');
    const data = await response.json();
    if (data.auth_url) {
        window.location.href = data.auth_url;
    } else {
        alert("Gagal mendapatkan URL otentikasi.");
    }
  };

  const handleAgentQuery = async (e: FormEvent) => {
    e.preventDefault();
    if (!command.trim() || !user) return;

    setIsAgentLoading(true);
    setAgentResponse('');

    try {
      const response = await fetch('/.netlify/functions/api/agent_handler', {
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
      
      fetchWeeklyTasks();

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
    <div style={{ maxWidth: '950px', margin: '40px auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Chronos Dashboard</h1>
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
          <div style={{marginTop: '10px'}}>
            <label htmlFor="file-upload" style={{marginRight: '15px'}}>Unggah Jadwal (PDF/Gambar):</label>
            <input 
              id="file-upload" 
              type="file" 
              accept="application/pdf,image/png,image/jpeg" 
              onChange={handleFileUpload} 
            />
          </div>
          <button 
              onClick={handleGoogleConnect} 
              style={{ padding: '10px 20px', cursor: 'pointer', background: '#4285F4', color: 'white', border: 'none', borderRadius: '4px', marginTop: '15px' }}>
              Hubungkan Google Calendar
          </button>
      </div>

      <div style={{ marginTop: '30px', border: '1px solid #ddd', padding: '20px', borderRadius: '8px', background: '#fff' }}>
        <h2>Aktivitas Minggu Ini</h2>
        <FullCalendar
          plugins={[timeGridPlugin, dayGridPlugin]}
          initialView="timeGridWeek"
          events={events}
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridWeek,timeGridDay'
          }}
          height="auto"
          locale="id"
          allDaySlot={false}
          nowIndicator={true}
        />
      </div>
    </div>
  );
}