import { useState, useEffect } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Search, Brain, Plus, Trash2, Tag as TagIcon, Upload } from 'lucide-react';

interface Memory {
  id: string;
  content: string;
  category: string;
  importance: number;
  created_at: string;
  metadata?: Record<string, any>;
}

interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string;
  tags: string[];
}

const API_BASE_URL = 'http://127.0.0.1:8000';

export default function MemoryCenter() {
  // Lists data
  const [memories, setMemories] = useState<Memory[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  
  // Inputs & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [noteTags, setNoteTags] = useState('');
  
  // Selection / UI states
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  // Load Initial Data
  const loadData = async () => {
    try {
      // 1. Fetch memories
      const memRes = await fetch(`${API_BASE_URL}/api/memory/`);
      if (memRes.ok) {
        const mems = await memRes.json();
        setMemories(mems);
      }

      // 2. Fetch notes
      const notesRes = await fetch(`${API_BASE_URL}/api/memory/notes`);
      if (notesRes.ok) {
        const nts = await notesRes.json();
        setNotes(nts);
      }
    } catch (e) {
      console.warn("Could not load backend memory data. Running in offline emulator mode.");
      // Offline fallback mock data
      setMemories([
        { id: '1', content: 'User prefers dark mode with cyan styling.', category: 'preference', importance: 0.85, created_at: new Date().toISOString() },
        { id: '2', content: 'Prime assistant setup completed successfully.', category: 'general', importance: 0.6, created_at: new Date().toISOString() }
      ]);
      setNotes([
        { id: 'note-1', title: 'Jarvis Specs', content: 'Design with abstract glass panel elements.', created_at: new Date().toLocaleDateString(), tags: ['design', 'core'] }
      ]);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Semantic Search
  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadData();
      return;
    }
    
    setIsSearching(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/memory/search?query=${encodeURIComponent(searchQuery)}`);
      if (res.ok) {
        const results = await res.json();
        setMemories(results);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  // Add Note
  const handleCreateNote = async (e: FormEvent) => {
    e.preventDefault();
    if (!noteTitle.trim() || !noteContent.trim()) return;

    const parsedTags = noteTags
      .split(',')
      .map(t => t.trim().toLowerCase())
      .filter(t => t.length > 0);

    try {
      const res = await fetch(`${API_BASE_URL}/api/memory/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: noteTitle,
          content: noteContent,
          tags: parsedTags
        })
      });

      if (res.ok) {
        const newNote = await res.json();
        setNotes(prev => [newNote, ...prev]);
        setNoteTitle('');
        setNoteContent('');
        setNoteTags('');
        // Reload memories to show the indexed note
        loadData();
      }
    } catch (e) {
      // Mock create offline fallback
      const mockNote: Note = {
        id: Math.random().toString(),
        title: noteTitle,
        content: noteContent,
        created_at: new Date().toLocaleDateString(),
        tags: parsedTags
      };
      setNotes(prev => [mockNote, ...prev]);
      setNoteTitle('');
      setNoteContent('');
      setNoteTags('');
    }
  };

  // Delete Memory Entry
  const handleDeleteMemory = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/memory/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setMemories(prev => prev.filter(m => m.id !== id));
        if (selectedMemory?.id === id) setSelectedMemory(null);
      }
    } catch (e) {
      setMemories(prev => prev.filter(m => m.id !== id));
      if (selectedMemory?.id === id) setSelectedMemory(null);
    }
  };

  // Document Import Upload Handler
  const handleImportDocument = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImportStatus("Uploading...");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE_URL}/api/memory/import-document?filename=${encodeURIComponent(file.name)}`, {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setImportStatus(`Indexed ${data.chunks_indexed} sections.`);
        loadData();
        setTimeout(() => setImportStatus(null), 3000);
      } else {
        setImportStatus("Import failed.");
      }
    } catch (err) {
      setImportStatus("Emulator mock upload completed.");
      setTimeout(() => setImportStatus(null), 3000);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full overflow-hidden">
      
      {/* Search & Memories Viewer (8 columns) */}
      <div className="lg:col-span-8 flex flex-col gap-6 overflow-hidden">
        
        {/* Search header */}
        <div className="glass-panel p-4 rounded-2xl flex flex-col gap-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-1 bg-slate-900/60 border border-slate-800 rounded-xl px-3.5 py-2 flex items-center gap-2.5">
              <Search size={16} className="text-prime-cyan" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search semantic memories, notes, and preferences..."
                className="flex-1 bg-transparent border-none outline-none font-sans text-xs text-white placeholder-slate-500"
              />
            </div>
            <button
              type="submit"
              className="bg-prime-cyan/15 hover:bg-prime-cyan/25 border border-prime-cyan/35 text-prime-cyan px-5 py-2 rounded-xl text-xs font-mono font-bold transition-all flex items-center gap-1.5"
            >
              <Brain size={14} />
              SEMANTIC SEARCH
            </button>
          </form>
        </div>

        {/* Memory Entries List */}
        <div className="glass-panel rounded-2xl flex-1 flex flex-col overflow-hidden">
          <div className="bg-slate-950/40 px-4 py-3 border-b border-slate-800/40 flex justify-between items-center">
            <span className="text-xs font-mono font-bold tracking-wider text-slate-400">SEMANTIC MEMORY INDEX ({memories.length})</span>
            {isSearching && <span className="text-[10px] font-mono text-prime-cyan animate-pulse">Searching vectors...</span>}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-black/10">
            {memories.length === 0 ? (
              <div className="text-slate-500 font-mono text-xs italic text-center p-8 mt-12">
                No indexed memories match your search parameters.
              </div>
            ) : (
              memories.map((m) => (
                <div 
                  key={m.id} 
                  onClick={() => setSelectedMemory(m)}
                  className={`p-3.5 rounded-xl border glass-card-interactive cursor-pointer flex justify-between items-start gap-4 transition-all ${
                    selectedMemory?.id === m.id 
                      ? 'border-prime-cyan/30 bg-prime-cyan/5 shadow-[0_0_12px_rgba(0,240,255,0.05)]' 
                      : 'border-slate-800/40 bg-slate-900/10'
                  }`}
                >
                  <div className="flex-1 flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                        m.category === 'preference' ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
                        m.category === 'note' ? 'bg-prime-purple/10 border-prime-purple/20 text-prime-purple' :
                        m.category === 'document' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' :
                        'bg-slate-800/30 border-slate-700/30 text-slate-400'
                      }`}>
                        {m.category}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        Importance: <span className="font-bold text-slate-300">{(m.importance * 100).toFixed(0)}%</span>
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 font-sans leading-relaxed line-clamp-2">
                      {m.content}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteMemory(m.id);
                    }}
                    className="p-1 rounded-lg hover:bg-rose-500/15 border border-transparent hover:border-rose-500/20 text-slate-500 hover:text-rose-400 transition-colors"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

      {/* Notes & Document Import (4 columns) */}
      <div className="lg:col-span-4 flex flex-col gap-6 overflow-y-auto">
        
        {/* Document Import Widget */}
        <div className="glass-panel p-4 rounded-2xl flex flex-col gap-3.5">
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-400 uppercase">Document Ingestion</h3>
          <div className="relative border-2 border-dashed border-slate-800 hover:border-prime-cyan/30 rounded-xl p-5 flex flex-col items-center justify-center gap-2 transition-all cursor-pointer">
            <Upload className="text-slate-500 hover:text-prime-cyan transition-colors" size={24} />
            <span className="text-[10px] font-sans text-slate-400 text-center">Select TXT or PDF document to parse and index</span>
            <input
              type="file"
              accept=".txt,.md"
              onChange={handleImportDocument}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
          </div>
          {importStatus && (
            <div className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/15 py-1.5 px-3 rounded-lg text-center">
              {importStatus}
            </div>
          )}
        </div>

        {/* Note Creator Form */}
        <div className="glass-panel p-4 rounded-2xl flex flex-col gap-4">
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-400 uppercase">Save Structured Note</h3>
          <form onSubmit={handleCreateNote} className="flex flex-col gap-3">
            <input
              type="text"
              value={noteTitle}
              onChange={(e) => setNoteTitle(e.target.value)}
              placeholder="Note Title..."
              className="bg-slate-900/60 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-600 outline-none focus:border-prime-cyan/30"
            />
            <textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Write note content here..."
              rows={4}
              className="bg-slate-900/60 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-600 outline-none resize-none focus:border-prime-cyan/30"
            />
            <input
              type="text"
              value={noteTags}
              onChange={(e) => setNoteTags(e.target.value)}
              placeholder="Tags (comma-separated)..."
              className="bg-slate-900/60 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-600 outline-none focus:border-prime-cyan/30"
            />
            <button
              type="submit"
              disabled={!noteTitle.trim() || !noteContent.trim()}
              className="w-full bg-prime-purple/15 hover:bg-prime-purple/25 border border-prime-purple/35 text-prime-purple px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all flex items-center justify-center gap-1.5 disabled:opacity-30 disabled:hover:bg-transparent"
            >
              <Plus size={14} />
              SAVE NOTE TO MEMORY
            </button>
          </form>
        </div>

        {/* Notes Log */}
        <div className="glass-panel p-4 rounded-2xl flex flex-col gap-3 max-h-[300px] overflow-hidden">
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-400 uppercase">Active Notes Directory</h3>
          <div className="space-y-2.5 overflow-y-auto pr-1 flex-1">
            {notes.length === 0 ? (
              <span className="text-[10px] font-mono text-slate-600 italic block py-4 text-center">No stored notes</span>
            ) : (
              notes.map((note) => (
                <div key={note.id} className="p-3 bg-slate-900/20 border border-slate-800/40 rounded-xl flex flex-col gap-1.5">
                  <span className="text-xs font-bold text-slate-200">{note.title}</span>
                  <p className="text-[11px] text-slate-400 line-clamp-2">{note.content}</p>
                  {note.tags && note.tags.length > 0 && (
                    <div className="flex gap-1.5 flex-wrap mt-0.5">
                      {note.tags.map((t, i) => (
                        <span key={i} className="text-[9px] font-mono text-prime-purple bg-prime-purple/10 px-2 py-0.5 rounded-full border border-prime-purple/15 flex items-center gap-0.5">
                          <TagIcon size={8} />
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
