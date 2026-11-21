import { formatToday, greeting } from "@/components/dashboard/dates";
import { Note } from "@/components/dashboard/Note";
import { getSession } from "@/lib/session";
import { listCases, loadCase, loadDashboard } from "../api";
import { L2Workspace } from "./L2Workspace";

// The Level 2 area officer landing page (UC-L2-01): the officer's own area by status, the cases with the one
// picked shown beside them, and what needs attention. Everything is read from the backend while the page is
// built, so the cards arrive filled in.
export async function L2Dashboard() {
  const [user, board, cases] = await Promise.all([
    getSession(),
    loadDashboard(),
    listCases({ status: null, severity: null, search: "", sort: "urgent", page: 1 }),
  ]);
  if (!user) return null; // the shell has already redirected unauthenticated visitors
  if (!board.ok) return <Note tone="alert">{board.message}</Note>;

  const data = board.data;
  const firstId = data.nextCaseId ?? (cases.ok ? cases.data.items[0]?.id : undefined);
  const first = firstId ? await loadCase(firstId) : null;
  const now = new Date();
  const urgent = data.urgent;

  return (
    <L2Workspace
      data={data}
      initialCases={cases.ok ? cases.data : undefined}
      initialCase={first?.ok ? first.data : null}
      date={`${formatToday(now)} · ${user.areaName ?? "Your"} area`}
      area={user.areaName ?? "your"}
      title={`${greeting(user.name, now)} ${urgent === 0 ? "No urgent case is" : `${urgent} urgent ${urgent === 1 ? "case is" : "cases are"}`} waiting for a decision.`}
      intro={`${data.counts.overdue} ${data.counts.overdue === 1 ? "case is" : "cases are"} past a time target. ${
        data.counts.forwarded
      } forwarded ${data.counts.forwarded === 1 ? "case has" : "cases have"} not been opened yet.`}
    />
  );
}
