import { AreaCoverage } from "./AreaCoverage";
import { ComplaintVolume } from "./ComplaintVolume";
import { MasterDataSummary } from "./MasterDataSummary";
import { MessageDelivery } from "./MessageDelivery";
import { NeedsAttention } from "./NeedsAttention";
import { PolicyLibrary } from "./PolicyLibrary";
import { PulseHero } from "./PulseHero";
import { RecentUsage } from "./RecentUsage";
import { Shortcuts } from "./Shortcuts";
import { SignInRhythm } from "./SignInRhythm";
import { SignedInNow } from "./SignedInNow";
import { StaffByRole } from "./StaffByRole";
import { getLiveData } from "./live-data";
import { adminDashboardSample } from "./sample-data";
import { Card, Chip, muted } from "@/components/dashboard/ui";

// The content of the administrator dashboard (UI-AD-01). One column on narrow
// screens, a 12-column bento grid from 1200px up.
// Signed-in figures, staff, sign-in activity and recent usage are live; the
// other tiles still show sample data until their modules exist.
export async function AdminDashboard() {
  const live = await getLiveData();

  if (!live) {
    return (
      <Card>
        <h2 className="text-[1.06rem] font-extrabold">The dashboard could not be loaded</h2>
        <p className={muted}>Check that the backend is running, then refresh the page.</p>
      </Card>
    );
  }

  const data = { ...adminDashboardSample, ...live };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[1.25rem] font-extrabold tracking-[-0.02em]">Today at a glance</h2>
        <Chip>Partly sample data</Chip>
      </div>

      <div className="grid grid-cols-1 gap-4 min-[1200px]:grid-cols-12">
        <PulseHero
          services={data.services}
          apiResponseMs={data.apiResponseMs}
          lastBackup={data.lastBackup}
          className="min-[1200px]:col-span-8"
        />
        <NeedsAttention items={data.attention} className="min-[1200px]:col-span-4" />

        <SignedInNow sessions={data.sessions} className="min-[1200px]:col-span-4" />
        <StaffByRole
          roles={data.staffByRole}
          portalUsers={data.portalUsers}
          deactivatedUsers={data.deactivatedUsers}
          className="min-[1200px]:col-span-8"
        />

        <SignInRhythm
          perHour={data.signInsPerHour}
          currentHour={data.currentHour}
          className="min-[1200px]:col-span-7"
        />
        <RecentUsage events={data.recentUsage} className="min-[1200px]:col-span-5" />

        <PolicyLibrary policy={data.policy} className="min-[1200px]:col-span-3" />
        <MessageDelivery messages={data.messages} className="min-[1200px]:col-span-3" />
        <AreaCoverage areas={data.areas} className="min-[1200px]:col-span-3" />
        <MasterDataSummary data={data.masterData} className="min-[1200px]:col-span-3" />

        <ComplaintVolume complaints={data.complaints} className="min-[1200px]:col-span-8" />
        <Shortcuts
          timeTargets={data.timeTargets}
          settings={data.settings}
          className="min-[1200px]:col-span-4"
        />
      </div>
    </div>
  );
}
