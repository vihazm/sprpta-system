import { api, type ApiResult } from "@/lib/api-client";

// The calls behind the Message templates screen (UC-AD, manage message templates).

const BASE = "/api/admin/message-templates";

export type MessageType = "registered" | "decided" | "closed" | "otp";
export type Channel = "sms" | "email";

export type Template = {
  messageType: MessageType;
  channel: Channel;
  label: string; // for example "MSG-1 Registered"
  when: string; // when the system sends it
  placeholders: string[]; // the {names} its text may use
  subject: string | null; // email only
  body: string;
  active: boolean;
  canSwitchOff: boolean; // the verification code is always sent
  edited: boolean; // false while it still has the default wording
  updatedAt: string | null;
  updatedBy: string | null;
};

type ApiTemplate = {
  message_type: MessageType;
  channel: Channel;
  label: string;
  when: string;
  placeholders: string[];
  subject: string | null;
  body: string;
  is_active: boolean;
  can_switch_off: boolean;
  edited: boolean;
  updated_at: string | null;
  updated_by: string | null;
};

function toTemplate(t: ApiTemplate): Template {
  return {
    messageType: t.message_type,
    channel: t.channel,
    label: t.label,
    when: t.when,
    placeholders: t.placeholders,
    subject: t.subject,
    body: t.body,
    active: t.is_active,
    canSwitchOff: t.can_switch_off,
    edited: t.edited,
    updatedAt: t.updated_at,
    updatedBy: t.updated_by,
  };
}

function mapData<A, B>(result: ApiResult<A>, convert: (data: A) => B): ApiResult<B> {
  return result.ok ? { ok: true, data: convert(result.data) } : result;
}

export async function loadTemplates() {
  return mapData(await api<ApiTemplate[]>(BASE), (list) => list.map(toTemplate));
}

export async function saveTemplate(t: Template, changes: { subject: string; body: string; active: boolean }) {
  const result = await api<ApiTemplate>(`${BASE}/${t.messageType}/${t.channel}`, {
    method: "PUT",
    body: { subject: t.channel === "email" ? changes.subject : null, body: changes.body, is_active: changes.active },
  });
  return mapData(result, toTemplate);
}
