import { getSession } from "@/lib/session";
import { DashboardProvider } from "./DashboardData";
import { DashboardView } from "./DashboardView";

// The Level 1 office staff landing page (UC-L1-12). The numbers are read from the backend in the browser, so
// they can be read again after a complaint is saved.
export async function L1Dashboard() {
  const user = await getSession();
  if (!user) return null; // the shell has already redirected unauthenticated visitors

  return (
    <DashboardProvider>
      <DashboardView name={user.name} />
    </DashboardProvider>
  );
}