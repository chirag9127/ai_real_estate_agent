import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listConversations, sendResults, sendMessage } from '../api/whatsapp';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorAlert from '../components/common/ErrorAlert';

export default function WhatsAppPage() {
  const [conversations, setConversations] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Send results form
  const [toNumber, setToNumber] = useState('');
  const [pipelineRunId, setPipelineRunId] = useState('');
  const [sendStatus, setSendStatus] = useState<string | null>(null);

  // Send message form
  const [msgTo, setMsgTo] = useState('');
  const [msgBody, setMsgBody] = useState('');
  const [msgStatus, setMsgStatus] = useState<string | null>(null);

  const webhookUrl =
    (import.meta.env.VITE_API_BASE_URL || `${window.location.origin}/api/v1`) +
    '/whatsapp/webhook';

  useEffect(() => {
    loadConversations();
  }, []);

  async function loadConversations() {
    try {
      const data = await listConversations();
      setConversations(data.conversations);
      setError(null);
    } catch {
      setError('Failed to load conversations.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSendResults(e: React.FormEvent) {
    e.preventDefault();
    setSendStatus(null);
    try {
      const result = await sendResults({
        to_number: toNumber,
        pipeline_run_id: Number(pipelineRunId),
      });
      setSendStatus(`Status: ${result.status}`);
    } catch {
      setSendStatus('Failed to send results.');
    }
  }

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    setMsgStatus(null);
    try {
      const result = await sendMessage({ to_number: msgTo, message: msgBody });
      setMsgStatus(`Status: ${result.status}`);
    } catch {
      setMsgStatus('Failed to send message.');
    }
  }

  if (loading) return <LoadingSpinner />;

  const conversationEntries = Object.entries(conversations);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to="/"
          className="text-[10px] uppercase tracking-[1px] opacity-50 hover:opacity-100 transition-opacity"
        >
          &larr; Back to Dashboard
        </Link>
        <h1 className="font-heading text-[32px] uppercase mt-2">WhatsApp Integration</h1>
        <p className="text-[12px] opacity-70 mt-1">
          Receive property requirements via WhatsApp and send results back to clients.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Webhook Setup */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">Webhook Setup</div>
        <div className="p-6 space-y-4">
          <div>
            <div className="text-[10px] uppercase tracking-[1px] opacity-50 mb-1">
              Twilio Webhook URL
            </div>
            <div className="font-mono text-[13px] bg-[#f2f2f2] border border-ink px-4 py-3 break-all select-all">
              {webhookUrl}
            </div>
          </div>
          <div className="text-[11px] opacity-70 space-y-2">
            <p>
              <strong>Setup instructions:</strong>
            </p>
            <ol className="list-decimal ml-5 space-y-1">
              <li>
                Go to the{' '}
                <a
                  href="https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                >
                  Twilio WhatsApp Sandbox
                </a>
              </li>
              <li>Set the &quot;When a message comes in&quot; webhook to the URL above</li>
              <li>Set the HTTP method to POST</li>
              <li>
                Configure <code>TWILIO_ACCOUNT_SID</code>, <code>TWILIO_AUTH_TOKEN</code>, and{' '}
                <code>TWILIO_WHATSAPP_NUMBER</code> in your backend <code>.env</code>
              </li>
              <li>Send a WhatsApp message to your Twilio number to start a property search</li>
            </ol>
          </div>
        </div>
      </section>

      {/* Active Conversations */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink flex justify-between items-center">
          <div className="font-heading uppercase">
            Active Conversations ({conversationEntries.length})
          </div>
          <button
            onClick={loadConversations}
            className="px-3 py-1 border border-ink text-[10px] uppercase tracking-[1px] cursor-pointer hover:bg-ink hover:text-surface transition-colors"
          >
            Refresh
          </button>
        </div>
        {conversationEntries.length === 0 ? (
          <div className="p-6 text-[11px] uppercase opacity-50">
            No active WhatsApp conversations. Send a message to your Twilio number to start one.
          </div>
        ) : (
          <div>
            {conversationEntries.map(([number, runId]) => (
              <div
                key={number}
                className="grid grid-cols-[1fr_1fr_80px] border-b border-ink/20 items-center"
              >
                <div className="px-6 py-3">
                  <span className="font-mono text-[13px]">{number}</span>
                </div>
                <div className="px-6 py-3">
                  <Link
                    to={`/pipeline/${runId}`}
                    className="text-[11px] uppercase tracking-[1px] underline"
                  >
                    Pipeline #{runId}
                  </Link>
                </div>
                <div className="px-6 py-3 text-right">
                  <span className="inline-block w-2 h-2 rounded-full bg-accent-green" />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Send Results */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Send Pipeline Results via WhatsApp
        </div>
        <form onSubmit={handleSendResults} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] uppercase tracking-[1px] opacity-50 block mb-1">
                WhatsApp Number
              </label>
              <input
                type="text"
                value={toNumber}
                onChange={(e) => setToNumber(e.target.value)}
                placeholder="whatsapp:+1234567890"
                className="w-full border border-ink px-3 py-2 text-[13px] font-mono bg-transparent"
                required
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-[1px] opacity-50 block mb-1">
                Pipeline Run ID
              </label>
              <input
                type="number"
                value={pipelineRunId}
                onChange={(e) => setPipelineRunId(e.target.value)}
                placeholder="1"
                className="w-full border border-ink px-3 py-2 text-[13px] font-mono bg-transparent"
                required
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              type="submit"
              className="px-4 py-2 bg-accent-green text-ink text-[11px] uppercase tracking-[1px] border border-ink cursor-pointer hover:opacity-80 transition-opacity"
            >
              Send Results
            </button>
            {sendStatus && (
              <span className="text-[11px] opacity-70">{sendStatus}</span>
            )}
          </div>
        </form>
      </section>

      {/* Send Custom Message */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Send Custom Message
        </div>
        <form onSubmit={handleSendMessage} className="p-6 space-y-4">
          <div>
            <label className="text-[10px] uppercase tracking-[1px] opacity-50 block mb-1">
              WhatsApp Number
            </label>
            <input
              type="text"
              value={msgTo}
              onChange={(e) => setMsgTo(e.target.value)}
              placeholder="whatsapp:+1234567890"
              className="w-full border border-ink px-3 py-2 text-[13px] font-mono bg-transparent"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[1px] opacity-50 block mb-1">
              Message
            </label>
            <textarea
              value={msgBody}
              onChange={(e) => setMsgBody(e.target.value)}
              placeholder="Type your message..."
              rows={3}
              className="w-full border border-ink px-3 py-2 text-[13px] font-mono bg-transparent resize-y"
              required
            />
          </div>
          <div className="flex items-center gap-4">
            <button
              type="submit"
              className="px-4 py-2 bg-ink text-surface text-[11px] uppercase tracking-[1px] cursor-pointer hover:opacity-80 transition-opacity"
            >
              Send Message
            </button>
            {msgStatus && (
              <span className="text-[11px] opacity-70">{msgStatus}</span>
            )}
          </div>
        </form>
      </section>
    </div>
  );
}
