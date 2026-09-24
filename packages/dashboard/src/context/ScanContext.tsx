import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, type ScanDetail, type ScanListItem } from "@/lib/api";

interface ScanContextValue {
  scans: ScanListItem[];
  current: ScanDetail | null;
  currentId: number | null;
  setCurrentId: (id: number | null) => void;
  loading: boolean;
  error: string | null;
  refreshList: () => Promise<void>;
  refreshCurrent: (id?: number | null) => Promise<void>;
}

const ScanContext = createContext<ScanContextValue | null>(null);

export function ScanProvider({ children }: { children: React.ReactNode }) {
  const [scans, setScans] = useState<ScanListItem[]>([]);
  const [current, setCurrent] = useState<ScanDetail | null>(null);
  const [currentId, setCurrentId] = useState<number | null>(() => {
    const raw = sessionStorage.getItem("sentinel.currentScan");
    const parsed = raw ? Number(raw) : NaN;
    return Number.isFinite(parsed) ? parsed : null;
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const currentIdRef = useRef(currentId);
  currentIdRef.current = currentId;

  const refreshList = async () => {
    try {
      const items = await api.listScans();
      setScans(items);
      setError(null);
      if (items.length > 0 && (currentId === null || !items.some((item) => item.id === currentId))) {
        const completed = items.find((item) => item.status === "completed") ?? items[0];
        setCurrentId(completed.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scans");
    } finally {
      setLoading(false);
    }
  };

  const refreshCurrent = async (id: number | null = currentIdRef.current) => {
    if (id === null) {
      setCurrent(null);
      return;
    }
    const detail = await api.getScan(id);
    setCurrent(detail);
  };

  useEffect(() => {
    if (currentId !== null) {
      sessionStorage.setItem("sentinel.currentScan", String(currentId));
    }
  }, [currentId]);

  useEffect(() => {
    void refreshList();
  }, []);

  useEffect(() => {
    if (currentId === null) {
      setCurrent(null);
      return;
    }
    void refreshCurrent().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Failed to load scan");
    });
  }, [currentId]);

  useEffect(() => {
    if (current?.status !== "running") return;
    const timer = window.setInterval(() => {
      void refreshCurrent().catch(() => undefined);
      void refreshList().catch(() => undefined);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [current?.status, currentId]);

  const value = useMemo(
    () => ({
      scans,
      current,
      currentId,
      setCurrentId,
      loading,
      error,
      refreshList,
      refreshCurrent,
    }),
    [scans, current, currentId, loading, error],
  );

  return <ScanContext.Provider value={value}>{children}</ScanContext.Provider>;
}

export function useScans(): ScanContextValue {
  const ctx = useContext(ScanContext);
  if (!ctx) throw new Error("useScans must be used inside ScanProvider");
  return ctx;
}
