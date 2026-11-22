"use client";

import { useState } from "react";
import { DashboardHero, HeroButton } from "@/components/dashboard/DashboardHero";
import { CaseList } from "../CaseList";
import { STATUS_LABEL } from "../status";
import type { CaseDetail, CaseFilter, CasePage, DashboardData } from "../types";
import { AreaStatistics } from "./AreaStatistics";
import { CaseGlance } from "./CaseGlance";
import { OverdueAlerts } from "./OverdueAlerts";
import { RecommendationList } from "./RecommendationList";
import { StatusTiles } from "./StatusTiles";
import { TimeTargets } from "./TimeTargets";

// The dashboard's moving parts. It holds what the officer picks (the status filter and the case shown beside
// the list) so the tiles, the list, the case card and the alerts all follow the same choice.
export function L2Workspace({
  data,
  initialCases,
  initialCase,
  date,
  area,
  title,
  intro,
}: {
  data: DashboardData;
  initialCases?: CasePage;
  initialCase: CaseDetail | null;
  date: string;
  area: string;
  title: string;
  intro: string;
}) {
  const [status, setStatus] = useState<CaseFilter | null>(null);
  const [selected, setSelected] = useState<number | null>(initialCase?.id ?? null);
  // Pressing a status tile starts the list again: its own search and severity filter would otherwise hide cases the
  // tile counts. The list is read fresh then, so the first view that came with the page is only used once.
  const [listStart, setListStart] = useState(0);
  const open = data.counts.all - data.counts.closed - data.counts.escalated;

  return (
    <div className="flex flex-col gap-4">
      <DashboardHero
        date={date}
        title={title}
        intro={intro}
        actions={
          <>
            {data.nextCaseId && (
              <HeroButton filled href={`/l2/cases/${data.nextCaseId}`}>
                Open next urgent case
              </HeroButton>
            )}
            <HeroButton href="/l2/cases">See all cases</HeroButton>
          </>
        }
        summaryTitle="Your day so far"
        tiles={[
          { value: data.arrivedToday, label: "Arrived today" },
          { value: data.decidedToday, label: "Decided today" },
          { value: data.counts.overdue, label: "Overdue" },
        ]}
        summaryNote={`${data.closedThisMonth} closed this month · ${open} still open${
          data.averageDecideDays !== null ? ` · decided in ${data.averageDecideDays} days on average` : ""
        }`}
      />

      <StatusTiles
        counts={data.counts}
        active={status}
        onPick={(s) => {
          setStatus(status === s ? null : s);
          setListStart(listStart + 1);
        }}
      />

      <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
        <CaseList
          key={listStart}
          title="Cases"
          subtitle={status ? `Filtered by ${status === "overdue" ? "Overdue" : STATUS_LABEL[status]}` : `Every case forwarded to the ${area} area`}
          status={status}
          onStatus={setStatus}
          initial={listStart === 0 ? initialCases : undefined}
          selected={selected}
          onSelect={(row) => setSelected(row.id)}
          className="min-[1200px]:col-span-8"
        />

        <div className="flex min-w-0 flex-col gap-4 min-[1200px]:col-span-4">
          <CaseGlance key={selected ?? "none"} caseId={selected} initial={initialCase} />
          <OverdueAlerts cases={data.overdue} total={data.counts.overdue} onOpen={setSelected} />
        </div>

        <RecommendationList items={data.recommendations} className="min-[1200px]:col-span-7" />
        <TimeTargets targets={data.targets} averageDays={data.averageDecideDays} className="min-[1200px]:col-span-5" />

        <AreaStatistics stats={data.statistics} area={area} className="min-[1200px]:col-span-12" />
      </div>
    </div>
  );
}
