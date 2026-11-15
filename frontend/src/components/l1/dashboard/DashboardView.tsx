"use client";

import { useEffect, useRef, useState } from "react";
import { formatToday, greeting } from "@/components/dashboard/dates";
import { DashboardHero, HeroButton } from "@/components/dashboard/DashboardHero";
import { Icon } from "@/components/dashboard/icons";
import type { FormOptions } from "@/components/l1/entry/types";
import { loadOverview, type Analytics } from "./api";
import { useDashboard } from "./DashboardData";
import { ComplaintSources } from "./ComplaintSources";
import { ComplaintAnalytics } from "./ComplaintAnalytics";
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
import type { DashboardOverview } from "./types";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

// The lower cards (sources, passed to Level 2, transport and severity, recently forwarded). They are read again
// whenever the dashboard numbers are, for example after a complaint was forwarded.
function useOverview(trigger: unknown, initial?: DashboardOverview): DashboardOverview | undefined {
  const [overview, setOverview] = useState<DashboardOverview | undefined>(initial);
  const firstShown = useRef(initial !== undefined); // the page came with these already
  useEffect(() => {
    if (firstShown.current) {
      firstShown.current = false;
      return;
    }
    let current = true;
    void loadOverview().then((result) => {
      if (current && result.ok) setOverview(result.data);
    });
    return () => {
      current = false;
    };
  }, [trigger]);
  return overview;
}

// The Level 1 office staff landing page (UC-L1-12). Every figure and card is live: PostgreSQL aggregates over the
// signed-in officer's own complaints, and the shared Level 1 queues.
// `initial` is what the server read while building the page; whatever is missing is read here in the browser.
export type DashboardInitial = { overview?: DashboardOverview; analytics?: Analytics; options?: FormOptions };

export function DashboardView({ name, initial }: { name: string; initial: DashboardInitial }) {
  const { data, error, loading, refresh } = useDashboard();
  const overview = useOverview(data, initial.overview);
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
        <QuickEntry className="min-[1200px]:col-span-8" options={initial.options} />
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
        <ComplaintAnalytics className="min-[1200px]:col-span-12" initial={initial.analytics} />

        <RecommendationForm className="min-[1200px]:col-span-4" initialMediums={initial.options?.mediums} />
        <ComplaintSources
          sources={overview?.sources}
          busiest={overview?.busiestWeek}
          className="min-[1200px]:col-span-4"
        />
        <QuickLookup className="min-[1200px]:col-span-4" />

        <PassedToLevel2 areas={overview?.areas} className="min-[1200px]:col-span-7" />
        <TransportSeverity
          transport={overview?.transport}
          severity={overview?.severity}
          className="min-[1200px]:col-span-5"
        />

        <RecentlyForwarded cases={overview?.forwarded} className="min-[1200px]:col-span-12" />
      </div>
    </div>
  );
}