import { api, type ApiResult } from "@/lib/api-client";

// The call behind the Statistics and reports page. The API speaks snake_case and the components camelCase, so the
// conversion happens here and nowhere else.

export type Filters = {
  from: string; // yyyy-mm-dd, or "" for no limit
  to: string;
  areaId: string; // an id, or "" for all
  categoryId: string;
  severityId: string;
  mediumId: string;
};

export type CountRow = { key: string; count: number };
export type Option = { id: number; name: string };
export type Stage = { targetDays: number | null; finished: number; onTime: number; averageDays: number | null };
export type TargetRow = { severity: string; forward: Stage; decide: Stage; close: Stage };

export type Statistics = {
  total: number;
  byStatus: CountRow[];
  byArea: CountRow[];
  byCategory: CountRow[];
  bySeverity: CountRow[];
  byMedium: CountRow[];
  byMonth: CountRow[];
  timeTargets: TargetRow[];
  overdue: { total: number; awaitingDecision: number; awaitingClose: number };
  options: { areas: Option[]; categories: Option[]; severities: Option[]; mediums: Option[] };
};

type StageIn = { target_days: number | null; finished: number; on_time: number; average_days: number | null };

type StatisticsIn = {
  total: number;
  by_status: CountRow[];
  by_area: CountRow[];
  by_category: CountRow[];
  by_severity: CountRow[];
  by_medium: CountRow[];
  by_month: CountRow[];
  time_targets: { severity: string; forward: StageIn; decide: StageIn; close: StageIn }[];
  overdue: { total: number; awaiting_decision: number; awaiting_close: number };
  options: Statistics["options"];
};

const toStage = (s: StageIn): Stage => ({
  targetDays: s.target_days,
  finished: s.finished,
  onTime: s.on_time,
  averageDays: s.average_days,
});

export async function loadStatistics(filters: Filters): Promise<ApiResult<Statistics>> {
  const params = new URLSearchParams();
  const set = (name: string, value: string) => value && params.set(name, value);
  set("date_from", filters.from);
  set("date_to", filters.to);
  set("area_id", filters.areaId);
  set("category_id", filters.categoryId);
  set("severity_id", filters.severityId);
  set("medium_id", filters.mediumId);

  const result = await api<StatisticsIn>(`/api/admin/statistics?${params}`);
  if (!result.ok) return result;
  const body = result.data;
  return {
    ok: true,
    data: {
      total: body.total,
      byStatus: body.by_status,
      byArea: body.by_area,
      byCategory: body.by_category,
      bySeverity: body.by_severity,
      byMedium: body.by_medium,
      byMonth: body.by_month,
      timeTargets: body.time_targets.map((row) => ({
        severity: row.severity,
        forward: toStage(row.forward),
        decide: toStage(row.decide),
        close: toStage(row.close),
      })),
      overdue: {
        total: body.overdue.total,
        awaitingDecision: body.overdue.awaiting_decision,
        awaitingClose: body.overdue.awaiting_close,
      },
      options: body.options,
    },
  };
}
