import { Card, muted } from "@/components/dashboard/ui";
import { UserDirectory } from "./UserDirectory";
import { UsersStats } from "./UsersStats";
import { loadUsers } from "./api";
import { getUsersSummary } from "./live-data";

// The content of the administrator's Users page (UI-AD-02). The figures and the first page of the
// directory are read together, as the page is built.
export async function UsersPage() {
  const [summary, firstPage] = await Promise.all([
    getUsersSummary(),
    loadUsers({ search: "", status: null, role: "all", page: 1 }),
  ]);

  if (!summary) {
    return (
      <Card>
        <h2 className="text-[1.06rem] font-extrabold">The users could not be loaded</h2>
        <p className={muted}>Check that the backend is running, then refresh the page.</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <UsersStats summary={summary} />
      <UserDirectory summary={summary} initial={firstPage.ok ? firstPage.data : undefined} />
    </div>
  );
}
