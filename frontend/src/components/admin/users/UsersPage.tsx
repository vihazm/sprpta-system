import { Card, muted } from "../dashboard/ui";
import { UserDirectory } from "./UserDirectory";
import { UsersStats } from "./UsersStats";
import { getUsersSummary } from "./live-data";

// The content of the administrator's Users page (UI-AD-02).
export async function UsersPage() {
  const summary = await getUsersSummary();

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
      <UserDirectory summary={summary} />
    </div>
  );
}
