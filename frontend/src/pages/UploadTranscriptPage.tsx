import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { uploadTranscript, pasteTranscript } from '../api/transcripts';
import { extractRequirements } from '../api/requirements';
import { getAuthUrl, listDocs, importDoc, type GoogleCredentials, type GoogleDocItem } from '../api/google';
import ErrorAlert from '../components/common/ErrorAlert';

type Tab = 'file' | 'paste' | 'google';

export default function UploadTranscriptPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState<Tab>(() => {
    const urlTab = searchParams.get('tab');
    return urlTab === 'google' ? 'google' : urlTab === 'paste' ? 'paste' : 'file';
  });
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [clientName, setClientName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // Google Docs state
  const [googleCreds, setGoogleCreds] = useState<GoogleCredentials | null>(() => {
    const stored = sessionStorage.getItem('google_credentials');
    return stored ? JSON.parse(stored) : null;
  });
  const [docs, setDocs] = useState<GoogleDocItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  // Load docs when Google tab is active and credentials exist
  useEffect(() => {
    if (tab === 'google' && googleCreds && docs.length === 0) {
      setDocsLoading(true);
      listDocs(googleCreds)
        .then(setDocs)
        .catch(() => setError('Failed to load Google Docs. Please reconnect.'))
        .finally(() => setDocsLoading(false));
    }
  }, [tab, googleCreds]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }, []);

  const handleConnectGoogle = async () => {
    setLoading(true);
    setError(null);
    try {
      const authUrl = await getAuthUrl();
      window.location.href = authUrl;
    } catch {
      setError('Failed to start Google authentication.');
      setLoading(false);
    }
  };

  const handleDisconnectGoogle = () => {
    sessionStorage.removeItem('google_credentials');
    setGoogleCreds(null);
    setDocs([]);
    setSelectedDocId(null);
  };

  const handleImportDoc = async (autoExtract: boolean) => {
    if (!googleCreds || !selectedDocId) {
      setError('Please select a document to import.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const transcript = await importDoc(googleCreds, selectedDocId);

      if (autoExtract) {
        await extractRequirements(transcript.id);
      }

      navigate(`/transcripts/${transcript.id}`);
    } catch {
      setError('Failed to import Google Doc. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (autoExtract: boolean) => {
    if (tab === 'google') {
      return handleImportDoc(autoExtract);
    }

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

      navigate(`/transcripts/${transcript.id}`);
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
            onClick={() => setTab('file')}
            className={`flex-1 py-4 text-[11px] uppercase tracking-[1px] text-center cursor-pointer transition-colors ${
              tab === 'file' ? 'bg-ink text-surface' : 'hover:bg-ink/5'
            }`}
          >
            File Upload
          </button>
          <button
            onClick={() => setTab('paste')}
            className={`flex-1 py-4 text-[11px] uppercase tracking-[1px] text-center cursor-pointer border-l border-ink transition-colors ${
              tab === 'paste' ? 'bg-ink text-surface' : 'hover:bg-ink/5'
            }`}
          >
            Paste Text
          </button>
          <button
            onClick={() => setTab('google')}
            className={`flex-1 py-4 text-[11px] uppercase tracking-[1px] text-center cursor-pointer border-l border-ink transition-colors ${
              tab === 'google' ? 'bg-ink text-surface' : 'hover:bg-ink/5'
            }`}
          >
            Google Docs
          </button>
        </div>

        <div className="p-6 space-y-4">
          {tab === 'file' ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
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
                    onClick={() => setFile(null)}
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
                      accept=".txt,.md,.pdf,.docx,.doc"
                      className="hidden"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                  </label>
                  <p className="text-[9px] uppercase opacity-40 mt-3">Accepts .txt, .md, .pdf, .docx, .doc files</p>
                </div>
              )}
            </div>
          ) : tab === 'paste' ? (
            <div className="space-y-4">
              <div>
                <label className="block text-[10px] uppercase tracking-[1px] mb-2">
                  Client Name (optional)
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
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
                  onChange={(e) => setText(e.target.value)}
                  rows={12}
                  className="w-full border border-ink bg-transparent px-4 py-3 text-[12px] font-mono focus:outline-none focus:ring-1 focus:ring-ink resize-none"
                  placeholder="Paste the call transcript here..."
                />
              </div>
            </div>
          ) : (
            /* Google Docs tab */
            <div className="space-y-4">
              {!googleCreds ? (
                <div className="border-2 border-dashed border-ink/30 p-12 text-center">
                  <p className="text-[11px] uppercase opacity-50 mb-4">
                    Connect your Google account to import documents
                  </p>
                  <button
                    onClick={handleConnectGoogle}
                    disabled={loading}
                    className="text-[11px] uppercase border border-ink px-6 py-3 rounded-full hover:bg-ink hover:text-surface transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {loading ? 'Connecting...' : 'Connect Google Docs'}
                  </button>
                </div>
              ) : (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-[10px] uppercase tracking-[1px] opacity-60">
                      Google Account Connected
                    </p>
                    <button
                      onClick={handleDisconnectGoogle}
                      className="text-[9px] uppercase border border-ink/40 px-3 py-1 rounded-full hover:bg-ink hover:text-surface transition-colors cursor-pointer"
                    >
                      Disconnect
                    </button>
                  </div>

                  {docsLoading ? (
                    <p className="text-center text-[11px] uppercase opacity-50 py-8">
                      Loading documents...
                    </p>
                  ) : docs.length === 0 ? (
                    <p className="text-center text-[11px] uppercase opacity-50 py-8">
                      No Google Docs found
                    </p>
                  ) : (
                    <div className="border border-ink/20 max-h-80 overflow-y-auto">
                      {docs.map((doc) => (
                        <button
                          key={doc.id}
                          onClick={() => setSelectedDocId(doc.id === selectedDocId ? null : doc.id)}
                          className={`w-full text-left px-4 py-3 border-b border-ink/10 last:border-b-0 transition-colors cursor-pointer ${
                            selectedDocId === doc.id
                              ? 'bg-ink text-surface'
                              : 'hover:bg-ink/5'
                          }`}
                        >
                          <p className="text-[12px] font-medium">{doc.name}</p>
                          <p className={`text-[9px] uppercase mt-1 ${
                            selectedDocId === doc.id ? 'opacity-70' : 'opacity-40'
                          }`}>
                            Modified {new Date(doc.modifiedTime).toLocaleDateString()}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {error && <ErrorAlert message={error} />}

          {tab === 'google' ? (
            googleCreds && selectedDocId && (
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => handleImportDoc(true)}
                  disabled={loading}
                  className="flex-1 py-3 bg-ink text-surface text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink/80 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Importing...' : 'Import & Extract'}
                </button>
                <button
                  onClick={() => handleImportDoc(false)}
                  disabled={loading}
                  className="py-3 px-6 border border-ink text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink/5 transition-colors disabled:opacity-50"
                >
                  Import Only
                </button>
              </div>
            )
          ) : (
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => handleSubmit(true)}
                disabled={loading}
                className="flex-1 py-3 bg-ink text-surface text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink/80 transition-colors disabled:opacity-50"
              >
                {loading ? 'Processing...' : 'Upload & Extract'}
              </button>
              <button
                onClick={() => handleSubmit(false)}
                disabled={loading}
                className="py-3 px-6 border border-ink text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink/5 transition-colors disabled:opacity-50"
              >
                Upload Only
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
