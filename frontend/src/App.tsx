import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import DashboardPage from './pages/DashboardPage';
import PipelineDetailPage from './pages/PipelineDetailPage';
import RankingsPage from './pages/RankingsPage';
import RequirementsPage from './pages/RequirementsPage';
import ReviewPage from './pages/ReviewPage';
import SearchResultsPage from './pages/SearchResultsPage';
import SendPage from './pages/SendPage';
import TranscriptDetailPage from './pages/TranscriptDetailPage';
import UploadTranscriptPage from './pages/UploadTranscriptPage';

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
      </Route>
    </Routes>
  );
}
