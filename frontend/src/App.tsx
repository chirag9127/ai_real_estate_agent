import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import DashboardPage from './pages/DashboardPage';
import UploadTranscriptPage from './pages/UploadTranscriptPage';
import TranscriptDetailPage from './pages/TranscriptDetailPage';
import RequirementsPage from './pages/RequirementsPage';
import SearchResultsPage from './pages/SearchResultsPage';
import RankingsPage from './pages/RankingsPage';
import ReviewPage from './pages/ReviewPage';
import SendPage from './pages/SendPage';
import PipelineDetailPage from './pages/PipelineDetailPage';
import WhatsAppPage from './pages/WhatsAppPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="upload" element={<UploadTranscriptPage />} />
        <Route path="transcripts/:id" element={<TranscriptDetailPage />} />
        <Route path="requirements/:id" element={<RequirementsPage />} />
        <Route path="pipeline/:runId" element={<PipelineDetailPage />} />
        <Route path="pipeline/:runId/search" element={<SearchResultsPage />} />
        <Route path="pipeline/:runId/rankings" element={<RankingsPage />} />
        <Route path="pipeline/:runId/review" element={<ReviewPage />} />
        <Route path="pipeline/:runId/send" element={<SendPage />} />
        <Route path="whatsapp" element={<WhatsAppPage />} />
      </Route>
    </Routes>
  );
}
