"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { loadDashboard } from "./api";
import type { DashboardSummary } from "./types";

type DashboardState = {
  data: DashboardSummary | null;
  error: string | null; // why the numbers could not be loaded
  loading: boolean;
  refresh: () => void; // read the numbers again, for example after a complaint was saved
};

const DashboardContext = createContext<DashboardState>({ data: null, error: null, loading: false, refresh: () => {} });

/**
 * Holds the dashboard numbers, and reads them again whenever something calls refresh(). `initial` are the
 * numbers the server read while building the page; without them they are read here, in the browser.
 */
export function DashboardProvider({ initial, children }: { initial?: DashboardSummary; children: ReactNode }) {
  const [data, setData] = useState<DashboardSummary | null>(initial ?? null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!initial);
  const latest = useRef(0); // only the newest answer is used, whatever order they arrive in

  const refresh = useCallback(() => {
    const mine = ++latest.current;
    void loadDashboard().then((result) => {
      if (mine !== latest.current) return;
      setLoading(false);
      if (result.ok) {
        setData(result.data);
        setError(null);
      } else {
        setError(result.message);
      }
    });
  }, []);

  useEffect(() => {
    if (!initial) refresh();
  }, [refresh, initial]);

  const value = useMemo(() => ({ data, error, loading, refresh }), [data, error, loading, refresh]);
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard() {
  return useContext(DashboardContext);
}