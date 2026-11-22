import { connection } from "next/server";
import { Card, muted } from "@/components/dashboard/ui";
import { loadStatistics, type Filters } from "./api";
import { periodDates } from "./period";
import { StatisticsView } from "./StatisticsView";

// The content of the Statistics and reports page (UI-AD-11). The figures for the last 12 months are read as the
// page is built; changing a filter reads them again in the browser.
export async function StatisticsPage() {
  await connection(); // "the last 12 months" depends on today, so this is read for every request
  const filters: Filters = { ...periodDates("12m"), areaId: "", categoryId: "", severityId: "", mediumId: "" };
  const result = await loadStatistics(filters);

  if (!result.ok) {
    return (
      <Card>
        <h2 className="text-[1.06rem] font-extrabold">The statistics could not be loaded</h2>
        <p className={muted}>{result.message}</p>
      </Card>
    );
  }
  return <StatisticsView initial={result.data} initialFilters={filters} />;
}
