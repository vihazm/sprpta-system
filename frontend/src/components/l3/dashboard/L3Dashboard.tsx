import { ApprovalList } from "@/components/dashboard/ApprovalList";
import { BarCard } from "@/components/dashboard/BarCard";
import { formatToday } from "@/components/dashboard/dates";
import { DashboardHero, HeroButton, ReferenceSearch } from "@/components/dashboard/DashboardHero";
import { muted } from "@/components/dashboard/ui";
import { getSession } from "@/lib/session";
import { AiAnalyst } from "./AiAnalyst";
import { AuditTrail } from "./AuditTrail";
import { CaseStatusDonut } from "./CaseStatusDonut";
import { EscalatedToMe } from "./EscalatedToMe";
import { MonthlyVolume } from "./MonthlyVolume";
import { OverdueTargets } from "./OverdueTargets";
import { RatingAppeals } from "./RatingAppeals";
import { RatingBands } from "./RatingBands";
import { RecommendationManager } from "./RecommendationManager";
import { ReportGenerator } from "./ReportGenerator";
import { TeamRatings } from "./TeamRatings";
import { TransportModes } from "./TransportModes";
import { l3DashboardSample } from "./sample-data";

const share = (count: number, counts: { count: number }[]) =>
  (count / Math.max(...counts.map((c) => c.count))) * 100;

// The Level 3 chairman landing page (UC-L3-01): escalated cases, system-wide figures, ratings,
// recommendations, reports and the audit trail. It shows sample data until the complaints
// module exists.
export async function L3Dashboard() {
  const user = await getSession();
  if (!user) return null; // the shell has already redirected unauthenticated visitors

  const data = l3DashboardSample;
  const { month } = data;
  const topArea = data.areas.reduce((a, b) => (b.count > a.count ? b : a));
  const topSource = data.sources[0];
  const sourcesTotal = data.sources.reduce((sum, s) => sum + s.count, 0);

  return (
    <div className="flex flex-col gap-4">
      <DashboardHero
        date={`${formatToday(new Date())} · All areas`}
        title={`System overview. ${data.escalatedTotal} cases are waiting for your decision.`}
        intro={`${month.overdue} cases are past their time target and ${data.appeals.length} rating appeals are open.`}
        actions={
          <>
            <HeroButton filled>Decide escalated cases</HeroButton>
            <HeroButton>Generate a report</HeroButton>
            <ReferenceSearch />
          </>
        }
        summaryTitle="This month, all areas"
        tiles={[
          { value: month.received, label: "Received" },
          { value: `${Math.round((month.closed / month.received) * 100)}%`, label: "Closed" },
          { value: month.overdue, label: "Overdue" },
        ]}
        summaryNote={`${month.closed} closed · ${month.open} open · ${month.rejected} rejected · ${month.overdue} overdue`}
      />

      <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
        <EscalatedToMe
          cases={data.escalated}
          total={data.escalatedTotal}
          className="min-[1200px]:col-span-8"
        />
        <AiAnalyst ai={data.ai} className="min-[1200px]:col-span-4" />

        <MonthlyVolume months={data.volume} className="min-[1200px]:col-span-4" />
        <CaseStatusDonut
          statuses={data.statuses}
          overdue={month.overdue}
          overdueAtLevel2={data.overdueAtLevel2}
          className="min-[1200px]:col-span-4"
        />
        <TransportModes modes={data.transport} className="min-[1200px]:col-span-4" />

        <BarCard
          title="Complaints by area"
          subtitle="Received this month"
          labelWidth="6rem"
          items={data.areas.map((a) => ({ label: a.label, value: a.count, share: share(a.count, data.areas) }))}
          note={`${topArea.label} receives ${Math.round((topArea.count / month.received) * 100)}% of all complaints.`}
          className="min-[1200px]:col-span-4"
        />
        <BarCard
          title="How complaints arrive"
          subtitle="By medium"
          labelWidth="5.2rem"
          items={data.sources.map((s) => ({ label: s.label, value: s.count, share: share(s.count, data.sources) }))}
          note={`${Math.round((topSource.count / sourcesTotal) * 100)}% arrive by ${topSource.label}, the busiest medium, followed by ${data.sources[1].label.toLowerCase()}s.`}
          className="min-[1200px]:col-span-4"
        />
        <BarCard
          title="Why cases were rejected"
          subtitle={`${month.rejected} rejected this month`}
          labelWidth="8rem"
          items={data.rejections.map((r) => ({
            label: r.label,
            value: r.count,
            share: share(r.count, data.rejections),
            color: "#d9a30b",
          }))}
          note="A reason is required whenever a complaint is rejected. Duplicates name the earlier case. Rejected is final."
          className="min-[1200px]:col-span-4"
        />

        <OverdueTargets data={data} className="min-[1200px]:col-span-6" />
        <ApprovalList
          title="Awaiting my approval"
          subtitle="Cases you decided, marked done by implementing staff"
          badge={`${data.approvals.length} ready`}
          approvals={data.approvals}
          footnote="Only Approve closes a case, and a closed case is never reopened. Level 3 approves the cases it decided itself."
          className="min-[1200px]:col-span-6"
        />

        <TeamRatings ratings={data.ratings} className="min-[1200px]:col-span-8" />
        <RatingBands bands={data.bands} className="min-[1200px]:col-span-4" />

        <RatingAppeals appeals={data.appeals} className="min-[1200px]:col-span-5" />
        <RecommendationManager
          statuses={data.recommendationStatuses}
          items={data.recommendations}
          className="min-[1200px]:col-span-7"
        />

        <ReportGenerator className="min-[1200px]:col-span-5" />
        <AuditTrail entries={data.audit} className="min-[1200px]:col-span-7" />
      </div>

      <p className={`${muted} px-1.5`}>Sample data. Figures, names and records are placeholders.</p>
    </div>
  );
}
