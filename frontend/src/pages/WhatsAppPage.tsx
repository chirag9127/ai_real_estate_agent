import { useState, useEffect } from 'react';
import { listConversations, sendMessage } from '../api/whatsapp';


export default function WhatsAppPage() {
  const [conversations, setConversations] = useState<Map<string, number>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testToNumber, setTestToNumber] = useState('');
  const [testMessage, setTestMessage] = useState('');

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadConversations = async () => {
    try {
      const data = await listConversations();
      setConversations(new Map(Object.entries(data.conversations)));
      setError(null);
    } catch (err) {
      setError(`Failed to load conversations: ${err}`);
    }
  };

  const handleSendTestMessage = async () => {
    if (!testToNumber.trim() || !testMessage.trim()) {
      setError('Please enter both phone number and message');
      return;
    }

    setLoading(true);
    try {
      const result = await sendMessage({
        to_number: testToNumber,
        message: testMessage,
      });
      setError(null);
      setTestToNumber('');
      setTestMessage('');
      setError(`Message sent: ${JSON.stringify(result)}`);
      setTimeout(() => setError(null), 3000);
    } catch (err) {
      setError(`Failed to send message: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          WhatsApp Integration
        </div>
        <div className="p-6 text-[12px] leading-relaxed">
          <p>
            This page shows active WhatsApp conversations and allows you to test
            the integration. Users send property requirements via WhatsApp, and the
            system automatically triggers the full pipeline and sends results back.
          </p>
        </div>
      </section>

      {/* Active Conversations */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Active Conversations ({conversations.size})
        </div>
        {conversations.size === 0 ? (
          <div className="p-6 text-[12px] opacity-70">
            No active conversations. Users who send WhatsApp messages will appear here.
          </div>
        ) : (
          <div className="divide-y divide-ink">
            {Array.from(conversations.entries()).map(([number, runId]) => (
              <div key={number} className="p-6">
                <div className="font-mono text-[11px] mb-2">
                  <strong>From:</strong> {number}
                </div>
                <div className="font-mono text-[11px]">
                  <strong>Pipeline Run ID:</strong> {runId}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Test Message Sender */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Send Test Message
        </div>
        <div className="p-6 flex flex-col gap-4">
          <div>
            <label className="block text-[11px] uppercase font-heading mb-2">
              To Number (with or without whatsapp: prefix)
            </label>
            <input
              type="text"
              value={testToNumber}
              onChange={(e) => setTestToNumber(e.target.value)}
              placeholder="e.g. +14155238886 or whatsapp:+14155238886"
              className="w-full border border-ink p-3 text-[12px] font-mono"
            />
          </div>
          <div>
            <label className="block text-[11px] uppercase font-heading mb-2">
              Message
            </label>
            <textarea
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              placeholder="Enter test message..."
              rows={4}
              className="w-full border border-ink p-3 text-[12px] font-mono"
            />
          </div>
          <button
            onClick={handleSendTestMessage}
            disabled={loading}
            className="px-4 py-2 border border-ink text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink hover:text-surface transition-colors disabled:opacity-50"
          >
            {loading ? 'Sending...' : 'Send Test Message'}
          </button>
        </div>
      </section>

      {/* Error / Status Messages */}
      {error && (
        <div className="border border-ink bg-surface p-6">
          <div className="text-[12px] font-mono">{error}</div>
        </div>
      )}

      {/* Configuration Info */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Configuration
        </div>
        <div className="p-6 text-[12px]">
          <p className="mb-4">
            To use WhatsApp integration in production, configure these environment
            variables in <code className="font-mono">backend/.env</code>:
          </p>
          <pre className="bg-black text-green-400 p-4 font-mono text-[10px] overflow-x-auto mb-4">
{`TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+15551234567`}
          </pre>
          <p>
            Webhook URL to configure in Twilio Console:
          </p>
          <pre className="bg-black text-green-400 p-4 font-mono text-[10px] overflow-x-auto">
            {`${window.location.origin}/api/v1/whatsapp/webhook`}
          </pre>
        </div>
      </section>
    </div>
  );
}
