import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ScanProvider } from "@/context/ScanContext";
import { AIPentesterPage } from "@/pages/AIPentester";
import { ChainsPage } from "@/pages/Chains";
import { FindingDetailPage } from "@/pages/FindingDetail";
import { FindingsPage } from "@/pages/Findings";
import { HistoryPage } from "@/pages/History";
import { MatrixPage } from "@/pages/Matrix";
import { NewScanPage } from "@/pages/NewScan";
import { OverviewPage } from "@/pages/Overview";

export function App() {
  return (
    <ScanProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/new" element={<NewScanPage />} />
          <Route path="/findings" element={<FindingsPage />} />
          <Route path="/findings/:findingKey" element={<FindingDetailPage />} />
          <Route path="/matrix" element={<MatrixPage />} />
          <Route path="/chains" element={<ChainsPage />} />
          <Route path="/ai" element={<AIPentesterPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </ScanProvider>
  );
}
