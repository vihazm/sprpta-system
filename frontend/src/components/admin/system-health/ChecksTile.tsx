import { Card, eyebrow } from "../dashboard/ui";
import { formatAgo } from "./format";
import { RunChecksButton } from "./RunChecksButton";

export function ChecksTile({ checkedAt, className = "" }: { checkedAt: string | null; className?: string }) {
  return (
    <Card className={`justify-between !bg-crimson/10 !shadow-none ${className}`}>
      <div>
        <p className={`${eyebrow} !text-crimson-hover`}>Checks</p>
        <h3 className="mt-1.5 font-display text-[2.1rem] leading-[1.08] tracking-[-0.035em]">
          {checkedAt ? `Last checked ${formatAgo(checkedAt)}` : "Not checked yet"}
        </h3>
        <p className="mt-2 text-[0.78rem] leading-[1.45] text-crimson-deep">
          The web app, the API and the database are checked once a minute.
        </p>
      </div>
      <div>
        <RunChecksButton />
      </div>
    </Card>
  );
}
