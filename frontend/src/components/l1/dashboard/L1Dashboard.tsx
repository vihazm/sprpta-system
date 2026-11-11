import { formatToday, greeting } from "@/components/dashboard/dates";
import { DashboardHero, HeroButton, ReferenceSearch } from "@/components/dashboard/DashboardHero";
import { Icon } from "@/components/dashboard/icons";
import { muted } from "@/components/dashboard/ui";
import { getSession } from "@/lib/session";
import { ComplaintSources } from "./ComplaintSources";
import { NeedsAttention } from "./NeedsAttention";
import { PassedToLevel2 } from "./PassedToLevel2";
import { PortalQueue } from "./PortalQueue";
import { QuickEntry } from "./QuickEntry";
import { QuickLookup } from "./QuickLookup";
import { RecentlyForwarded } from "./RecentlyForwarded";
import { RecommendationForm } from "./RecommendationForm";
import { TransportSeverity } from "./TransportSeverity";
import { l1DashboardSample } from "./sample-data";

// The Level 1 office staff landing page (UC-L1-12): the queues, quick entry of a complaint,
// and a few figures. It shows sample data until the complaints module exists.
export async function L1Dashboard() {
  const user = await getSession();
  if (!user) return null; // the shell has already redirected unauthenticated visitors

  const data = l1DashboardSample;
  const now = new Date();
  const open = data.queues.reduce((sum, q) => sum + q.count, 0);
  const portal = data.queues.find((q) => q.kind === "portal")?.count ?? 0;

  return (
    <div className="flex flex-col gap-4">
      <DashboardHero
        date={formatToday(now)}
        title={`${greeting(user.name, now)} ${open} items need you today.`}
        intro={`${portal} portal submissions are waiting for your check, and ${open - portal} drafts and incomplete cases are still open.`}
        actions={
          <>
            <HeroButton filled>
              <Icon name="plus" size={14} />
              Log a new complaint
            </HeroButton>
            <HeroButton>Log a recommendation</HeroButton>
            <ReferenceSearch />
          </>
        }
        summaryTitle="Your day so far"
        tiles={[
          { value: data.day.entered, label: "Entered" },
          { value: data.day.forwarded, label: "Forwarded" },
          { value: data.day.stillOpen, label: "Still open" },
        ]}
        summaryNote={`${data.day.thisWeek} entered this week · ${data.day.thisMonth} this month`}
      />

      <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
        <QuickEntry draft={data.draft} className="min-[1200px]:col-span-8" />
        <div className="flex min-w-0 flex-col gap-4 min-[1200px]:col-span-4">
          <NeedsAttention queues={data.queues} waiting={data.waiting} />
          <PortalQueue submissions={data.portal} className="flex-1" />
        </div>

        <RecommendationForm className="min-[1200px]:col-span-4" />
        <ComplaintSources
          sources={data.sources}
          busiest={data.busiestThisWeek}
          className="min-[1200px]:col-span-4"
        />
        <QuickLookup lookup={data.lookup} className="min-[1200px]:col-span-4" />

        <PassedToLevel2 areas={data.areas} className="min-[1200px]:col-span-7" />
        <TransportSeverity
          transport={data.transport}
          severity={data.severity}
          className="min-[1200px]:col-span-5"
        />

        <RecentlyForwarded cases={data.forwarded} className="min-[1200px]:col-span-12" />
      </div>

      <p className={`${muted} px-1.5`}>Sample data. Figures, names and records are placeholders.</p>
    </div>
  );
}
