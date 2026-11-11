import { PulseHero } from "../dashboard/PulseHero";
import { Card, muted } from "../dashboard/ui";
import { ChecksTile } from "./ChecksTile";
import { PendingTile } from "./PendingTile";
import { RecentEvents } from "./RecentEvents";
import { ServiceTile } from "./ServiceTile";
import { UptimeTile } from "./UptimeTile";
import { getSystemHealth } from "./live-data";
import { PENDING_SERVICES, buildMetrics } from "./metrics";
import { heroServices } from "./status";

// The content of the administrator's System health page (UI-AD-07). One column on
// narrow screens, a 12-column bento grid from 1200px up. The web app, the API and the
// database are checked for real; the other services show as "not set up" until they exist.
export async function SystemHealth() {
  const data = await getSystemHealth();

  if (!data) {
    return (
      <Card>
        <h2 className="text-[1.06rem] font-extrabold">System health could not be loaded</h2>
        <p className={muted}>Check that the backend is running, then refresh the page.</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-[1.25rem] font-extrabold tracking-[-0.02em]">Services and uptime</h2>

      <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
        <PulseHero
          services={heroServices(data.services)}
          apiResponseMs={data.series.api}
          className="min-[1200px]:col-span-8"
        />
        <UptimeTile uptime={data.uptime} className="min-[1200px]:col-span-4" />

        {buildMetrics(data).map((metric) => (
          <ServiceTile key={metric.name} metric={metric} className="min-[1200px]:col-span-4" />
        ))}
        {PENDING_SERVICES.map((service) => (
          <PendingTile key={service.name} {...service} className="min-[1200px]:col-span-4" />
        ))}

        <RecentEvents events={data.events} className="min-[1200px]:col-span-7" />
        <ChecksTile checkedAt={data.checkedAt} className="min-[1200px]:col-span-5" />
      </div>
    </div>
  );
}
