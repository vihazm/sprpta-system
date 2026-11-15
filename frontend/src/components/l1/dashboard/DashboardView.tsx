"use client";

import { formatToday, greeting } from "@/components/dashboard/dates";
import { DashboardHero, HeroButton } from "@/components/dashboard/DashboardHero";
import { Icon } from "@/components/dashboard/icons";
import { muted } from "@/components/dashboard/ui";
import { useDashboard } from "./DashboardData";
import { ComplaintSources } from "./ComplaintSources";
import { ComplaintsByTarget } from "./ComplaintsByTarget";
import { NeedsAttention } from "./NeedsAttention";
import { PassedToLevel2 } from "./PassedToLevel2";
import { PortalQueue } from "./PortalQueue";
import { QuickEntry } from "./QuickEntry";
import { QuickLookup } from "./QuickLookup";
import { ReferenceFinder } from "./ReferenceFinder";
import { RecentlyForwarded } from "./RecentlyForwarded";
import { RecommendationForm } from "./RecommendationForm";
import { TransportSeverity } from "./TransportSeverity";
import { l1DashboardSample } from "./sample-data";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

// The Level 1 office staff landing page (UC-L1-12). The banner, Your day so far, Needs attention, the portal
// queue and Quick entry are live. The cards from "Where complaints come from" down still show sample figures.
export function DashboardView({ name }: { name: string }) {
  const { data, error, loading, refresh } = useDashboard();
  const sample = l1DashboardSample;
  const now = new Date();

  const waiting = data ? data.queues.drafts + data.queues.incomplete : 0;
  const open = data ? data.queues.portal + waiting : 0;
  const hello = greeting(name, now);
  const title = data ? `${hello} ${open === 1 ? "1 item needs" : `${open} items need`} you today.` : hello;
  const intro = data
    ? `${plural(data.queues.portal, "portal submission is", "portal submissions are")} waiting for your check, and ${plural(waiting, "draft or incomplete case is", "drafts and incomplete cases are")} still open.`
    : error
      ? "The numbers could not be loaded. Check that the backend is running, then refresh the page."
      : "Checking what is waiting for you…";
  const figure = (value: number | undefined) => (value === undefined ? "–" : value);

  return (
    <div className="flex flex-col gap-4">
      <DashboardHero
        date={formatToday(now)}
        title={title}
        intro={intro}
        actions={
          <>
            <HeroButton filled href="/l1/new-complaint">
              <Icon name="plus" size={14} />
              Log a new complaint
            </HeroButton>
            <HeroButton href="/l1/new-recommendation">Log a recommendation</HeroButton>
            <ReferenceFinder />
          </>
        }
        summaryTitle="Your day so far"
        tiles={[
          { value: figure(data?.day.entered), label: "Entered" },
          { value: figure(data?.day.forwarded), label: "Forwarded" },
          { value: figure(data?.day.stillOpen), label: "Still open" },
        ]}
        summaryNote={
          data
            ? `${data.weekEntered} entered this week · ${data.monthEntered} this month`
            : error
              ? "Your figures could not be loaded."
              : "Loading your figures…"
        }
      />

      <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
        <QuickEntry className="min-[1200px]:col-span-8" />
        <div className="flex min-w-0 flex-col gap-4 min-[1200px]:col-span-4">
          <NeedsAttention summary={data} error={error} onRetry={refresh} />
          <PortalQueue
            submissions={data?.portal ?? []}
            waiting={data?.queues.portal ?? 0}
            loaded={!loading && data !== null}
            className="flex-1"
          />
        </div>

        <ComplaintsByTarget counts={data?.byTarget} className="min-[1200px]:col-span-12" />

        <RecommendationForm className="min-[1200px]:col-span-4" />
        <ComplaintSources
          sources={sample.sources}
          busiest={sample.busiestThisWeek}
          className="min-[1200px]:col-span-4"
        />
        <QuickLookup lookup={sample.lookup} className="min-[1200px]:col-span-4" />

        <PassedToLevel2 areas={sample.areas} className="min-[1200px]:col-span-7" />
        <TransportSeverity
          transport={sample.transport}
          severity={sample.severity}
          className="min-[1200px]:col-span-5"
        />

        <RecentlyForwarded cases={sample.forwarded} className="min-[1200px]:col-span-12" />
      </div>

      <p className={`${muted} px-1.5`}>
        The cards from &ldquo;Where complaints come from&rdquo; down still show sample data. Their figures, names and
        records are placeholders.
      </p>
    </div>
  );
}