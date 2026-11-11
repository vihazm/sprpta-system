import { ApprovalList } from "@/components/dashboard/ApprovalList";
import { formatToday, greeting } from "@/components/dashboard/dates";
import { DashboardHero, HeroButton, ReferenceSearch } from "@/components/dashboard/DashboardHero";
import { muted } from "@/components/dashboard/ui";
import { getSession } from "@/lib/session";
import { AreaWorkload } from "./AreaWorkload";
import { CaseReview } from "./CaseReview";
import { CasesByStage } from "./CasesByStage";
import { EscalatedCases } from "./EscalatedCases";
import { RecentlyClosed } from "./RecentlyClosed";
import { RecommendationList } from "./RecommendationList";
import { TimeTargets } from "./TimeTargets";
import { UnclosedCases } from "./UnclosedCases";
import { UrgentCases } from "./UrgentCases";
import { l2DashboardSample } from "./sample-data";

// The Level 2 area officer landing page (UC-L2-01): the officer's own area, the case being
// reviewed with its decision form, and the work waiting. It shows sample data until the
// complaints module exists.
export async function L2Dashboard() {
  const user = await getSession();
  if (!user) return null; // the shell has already redirected unauthenticated visitors

  const data = l2DashboardSample;
  const now = new Date();
  const area = user.areaName ?? "your";
  const urgent = data.urgent.filter((c) => c.severity === "critical").length;
  const overdue = data.urgent.filter((c) => c.overdue).length;

  return (
    <div className="flex flex-col gap-4">
      <DashboardHero
        date={`${formatToday(now)} · ${area} area`}
        title={`${greeting(user.name, now)} ${urgent} urgent ${urgent === 1 ? "case needs" : "cases need"} a decision.`}
        intro={`${overdue} ${overdue === 1 ? "case is" : "cases are"} past its time target. ${data.approvals.length} completed jobs are waiting for your approval.`}
        actions={
          <>
            <HeroButton filled>Open next urgent case</HeroButton>
            <HeroButton>Approve completed cases</HeroButton>
            <ReferenceSearch />
          </>
        }
        summaryTitle="Your day so far"
        tiles={[
          { value: data.day.arrived, label: "Arrived today" },
          { value: data.day.decided, label: "Decided" },
          { value: data.approvals.length, label: "Awaiting approval" },
        ]}
        summaryNote={`${data.month.closed} closed this month · ${data.month.open} still open · ${data.month.overdue} overdue`}
      />

      <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
        <CaseReview review={data.caseToReview} className="min-[1200px]:col-span-8" />
        <div className="flex min-w-0 flex-col gap-4 min-[1200px]:col-span-4">
          <CasesByStage stages={data.stages} area={area} />
          <UrgentCases cases={data.urgent} className="flex-1" />
        </div>

        <AreaWorkload data={data} area={area} className="min-[1200px]:col-span-4" />
        <ApprovalList
          title="Awaiting my approval"
          subtitle={`${data.approvals.length} jobs marked done by implementing staff`}
          approvals={data.approvals}
          footnote={`${data.moreWithStaff} more decisions are still with implementing staff. Only Approve closes a case, and a closed case is never reopened.`}
          className="min-[1200px]:col-span-4"
        />
        <UnclosedCases data={data} className="min-[1200px]:col-span-4" />

        <RecommendationList items={data.recommendations} className="min-[1200px]:col-span-4" />
        <EscalatedCases cases={data.escalated} className="min-[1200px]:col-span-4" />
        <TimeTargets targets={data.targets} className="min-[1200px]:col-span-4" />

        <RecentlyClosed cases={data.closed} className="min-[1200px]:col-span-12" />
      </div>

      <p className={`${muted} px-1.5`}>Sample data. Figures, names and records are placeholders.</p>
    </div>
  );
}
