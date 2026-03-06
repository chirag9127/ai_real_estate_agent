import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { exchangeCode } from '../api/google';

export default function GoogleCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setError('No authorization code received from Google.');
      return;
    }

    exchangeCode(code)
      .then((credentials) => {
        sessionStorage.setItem('google_credentials', JSON.stringify(credentials));
        navigate('/upload?tab=google', { replace: true });
      })
      .catch(() => {
        setError('Failed to exchange authorization code. Please try again.');
      });
  }, [searchParams, navigate]);

  if (error) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center space-y-4">
        <p className="text-[11px] uppercase tracking-[1px] text-red-600">{error}</p>
        <button
          onClick={() => navigate('/upload')}
          className="text-[11px] uppercase border border-ink px-4 py-2 rounded-full hover:bg-ink hover:text-surface transition-colors cursor-pointer"
        >
          Back to Upload
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-20 text-center">
      <p className="text-[11px] uppercase tracking-[1px] opacity-60">
        Connecting to Google Docs...
      </p>
    </div>
  );
}
