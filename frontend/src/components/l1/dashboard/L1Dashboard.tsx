import { loadOptions } from "@/components/l1/entry/api";
import type { ApiResult } from "@/lib/api-client";
import { getSession } from "@/lib/session";
import { loadAnalytics, loadDashboard, loadOverview } from "./api";
import { DashboardProvider } from "./DashboardData";
import { DashboardView } from "./DashboardView";

// What was read, or nothing when it could not be: the browser then reads that part itself, as it always did.
const dataOf = <T,>(result: ApiResult<T>) => (result.ok ? result.data : undefined);

// The Level 1 office staff landing page (UC-L1-12). Every figure is read from the backend together, while the
// page is built, so the cards arrive filled in. The browser reads them again after a complaint is saved.
export async function L1Dashboard() {
  const [user, summary, overview, analytics, options] = await Promise.all([
    getSession(),
    loadDashboard(),
    loadOverview(),
    loadAnalytics(),
    loadOptions(),
  ]);
  if (!user) return null; // the shell has already redirected unauthenticated visitors

  return (
    <DashboardProvider initial={dataOf(summary)}>
      <DashboardView
        name={user.name}
        initial={{ overview: dataOf(overview), analytics: dataOf(analytics), options: dataOf(options) }}
      />
    </DashboardProvider>
  );
}
