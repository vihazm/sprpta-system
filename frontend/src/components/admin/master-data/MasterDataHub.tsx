import Link from "next/link";
import { formatNumber } from "@/components/admin/dashboard/format";
import { Card, Chip, bigNumber, muted } from "@/components/dashboard/ui";
import { Icon } from "@/components/dashboard/icons";
import { loadCounts } from "./api";
import { ENTITIES } from "./entities";

// The master data hub (UI-AD-04): one card per kind of record, with how many there are. A card opens its list.
export async function MasterDataHub() {
  const result = await loadCounts();
  if (!result.ok) {
    return (
      <Card>
        <h2 className="text-[1.06rem] font-extrabold">The master data could not be loaded</h2>
        <p className={muted}>{result.message}</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-[1.25rem] font-extrabold tracking-[-0.015em]">Master data</h2>
        <p className={`mt-0.5 ${muted}`}>The lists Level 1 looks complaints up in. Choose one to search or edit it.</p>
      </div>
      <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 min-[640px]:grid-cols-2 min-[1200px]:grid-cols-4">
        {result.data.map(({ key, total, active }) => (
          <li key={key}>
            <Link
              href={`/admin/master-data/${key}`}
              className="focus-ring group flex h-full flex-col gap-3 rounded-[1.75rem] bg-white p-6 shadow-[0_1px_2px_rgba(60,20,30,0.05),0_22px_44px_-30px_rgba(110,8,30,0.28),0_0_0_1px_rgba(60,20,30,0.03)] transition-shadow hover:shadow-[0_1px_2px_rgba(60,20,30,0.05),0_22px_44px_-30px_rgba(110,8,30,0.28),0_0_0_1.5px_rgba(179,17,47,0.35)]"
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-[1.06rem] font-extrabold tracking-[-0.015em]">{ENTITIES[key].title}</h3>
                <span className="text-muted transition-colors group-hover:text-crimson">
                  <Icon name="next" />
                </span>
              </div>
              <p className={muted}>{ENTITIES[key].blurb}</p>
              <div className="mt-auto flex items-end justify-between gap-2">
                <span className={`${bigNumber} text-[2.1rem]`}>{formatNumber(total)}</span>
                {total > active && <Chip tone="warn">{formatNumber(total - active)} inactive</Chip>}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
