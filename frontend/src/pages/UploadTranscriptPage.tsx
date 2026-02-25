import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { extractRequirements } from '../api/requirements';
import { uploadTranscript, pasteTranscript } from '../api/transcripts';
import ErrorAlert from '../components/common/ErrorAlert';

export default function UploadTranscriptPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<'file' | 'paste'>('file');
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [clientName, setClientName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0] as File | undefined;
    if (file) {
      setFile(file);
    }
  }, []);

  const handleSubmit = async (autoExtract: boolean) => {
    setLoading(true);
    setError(null);
    try {
      let transcript;
      if (tab === 'file' && file) {
        transcript = await uploadTranscript(file);
      } else if (tab === 'paste' && text.trim()) {
        transcript = await pasteTranscript(text, clientName || undefined);
      } else {
        setError('Please provide a transcript file or text.');
        setLoading(false);
        return;
      }

      if (autoExtract) {
        await extractRequirements(transcript.id);
      }

      void navigate(`/transcripts/${transcript.id}`);
    } catch {
      setError('Failed to upload transcript. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="font-heading text-[32px] uppercase">Upload Call Transcript</h1>

      <div className="border border-ink bg-surface">
        {/* Tab switcher */}
        <div className="flex border-b border-ink">
          <button
            onClick={() => { setTab('file'); }}
            className={`flex-1 py-4 text-[11px] uppercase tracking-[1px] text-center cursor-pointer transition-colors ${
              tab === 'file' ? 'bg-ink text-surface' : 'hover:bg-ink/5'
            }`}
          >
            File Upload
          </button>
          <button
            onClick={() => { setTab('paste'); }}
            className={`flex-1 py-4 text-[11px] uppercase tracking-[1px] text-center cursor-pointer border-l border-ink transition-colors ${
              tab === 'paste' ? 'bg-ink text-surface' : 'hover:bg-ink/5'
            }`}
          >
            Paste Text
          </button>
        </div>

        <div className="p-6 space-y-4">
          {tab === 'file' ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => { setDragOver(false); }}
              onDrop={handleDrop}
              className={`border-2 border-dashed p-12 text-center transition-colors ${
                dragOver ? 'border-accent-orange bg-accent-orange/5' : 'border-ink/30 hover:border-ink/60'
              }`}
            >
              {file ? (
                <div>
                  <p className="font-heading text-[18px] uppercase">{file.name}</p>
                  <p className="text-[10px] uppercase opacity-70 mt-1">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                  <button
                    onClick={() => { setFile(null); }}
                    className="mt-3 text-[10px] uppercase border border-ink px-3 py-1 rounded-full hover:bg-ink hover:text-surface transition-colors cursor-pointer"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-[11px] uppercase opacity-50">
                    Drag and drop a transcript file here, or
                  </p>
                  <label className="mt-3 inline-block cursor-pointer text-[11px] uppercase border border-ink px-4 py-2 rounded-full hover:bg-ink hover:text-surface transition-colors">
                    Browse Files
                    <input
                      type="file"
                      accept=".txt,.md"
                      className="hidden"
                      onChange={(e) => { setFile(e.target.files?.[0] ?? null); }}
                    />
                  </label>
                  <p className="text-[9px] uppercase opacity-40 mt-3">Accepts .txt, .md files</p>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-[10px] uppercase tracking-[1px] mb-2">
                  Client Name (optional)
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => { setClientName(e.target.value); }}
                  className="w-full border border-ink bg-transparent px-4 py-3 text-[12px] focus:outline-none focus:ring-1 focus:ring-ink"
                  placeholder="e.g., John Smith"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-[1px] mb-2">
                  Transcript Text
                </label>
                <textarea
                  value={text}
                  onChange={(e) => { setText(e.target.value); }}
                  rows={12}
                  className="w-full border border-ink bg-transparent px-4 py-3 text-[12px] font-mono focus:outline-none focus:ring-1 focus:ring-ink resize-none"
                  placeholder="Paste the call transcript here..."
                />
              </div>
            </div>
          )}

          {error && <ErrorAlert message={error} />}

          <div className="flex gap-3 pt-2">
            <button
              onClick={() => {
                void handleSubmit(true);
              }}
              disabled={loading}
              className="flex-1 py-3 bg-ink text-surface text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink/80 transition-colors disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Upload & Extract'}
            </button>
            <button
              onClick={() => {
                void handleSubmit(false);
              }}
              disabled={loading}
              className="py-3 px-6 border border-ink text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink/5 transition-colors disabled:opacity-50"
            >
              Upload Only
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
