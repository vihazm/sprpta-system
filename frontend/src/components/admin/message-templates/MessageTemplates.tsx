import { Card, Chip, muted } from "@/components/dashboard/ui";
import { loadTemplates, type Template } from "./api";
import { TemplateEditor } from "./TemplateEditor";

// The Message templates screen: what complainants are sent and when, each as a text message and an email. A
// message goes by text when a phone number is on record, otherwise by email.
export async function MessageTemplates() {
  const result = await loadTemplates();
  if (!result.ok) {
    return (
      <Card>
        <h2 className="text-[1.06rem] font-extrabold">The message templates could not be loaded</h2>
        <p className={muted}>{result.message}</p>
      </Card>
    );
  }

  // One card per message, with its text message and its email side by side.
  const messages = new Map<string, Template[]>();
  for (const t of result.data) messages.set(t.messageType, [...(messages.get(t.messageType) ?? []), t]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-[1.25rem] font-extrabold tracking-[-0.015em]">Message templates</h2>
        <p className={`mt-0.5 ${muted}`}>
          The wording of the messages complainants receive. A message goes by text when a mobile number is on record,
          otherwise by email. Until SMS and email are connected, sent messages appear in the backend terminal.
        </p>
      </div>
      {[...messages.values()].map((channels) => {
        const { messageType, label, when, placeholders } = channels[0];
        return (
          <Card key={messageType}>
            <div className="flex flex-col gap-1.5">
              <h2 className="text-[1.06rem] font-extrabold tracking-[-0.015em]">{label}</h2>
              <p className={muted}>{when}</p>
              <p className={`${muted} flex flex-wrap items-center gap-1.5`}>
                Can use
                {placeholders.map((name) => (
                  <Chip key={name}>{`{${name}}`}</Chip>
                ))}
              </p>
            </div>
            <div className="grid grid-cols-1 gap-4 min-[1100px]:grid-cols-2">
              {channels.map((t) => (
                <TemplateEditor key={t.channel} initial={t} />
              ))}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
