"use client";

import { useRef, useState } from "react";
import { Icon } from "@/components/dashboard/icons";
import { eyebrow, muted } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
import { fileUrl, removeFile, uploadFile } from "./api";
import { ACCEPT, MAX_FILES, checkFile, formatSize, isImage, withKnownType } from "./files";
import type { PortalAttachment } from "./types";

/**
 * The files of one complaint. A photo shows as a picture, any other file as a small card; each opens in a new tab.
 * While SPRPTA has not started on the complaint, files can still be added or taken out.
 */
export function AttachmentGallery({
  complaintId,
  attachments,
  editable,
  onChange,
}: {
  complaintId: number;
  attachments: PortalAttachment[];
  editable: boolean;
  onChange: (next: PortalAttachment[]) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  if (attachments.length === 0 && !editable) return null;

  async function add(list: FileList) {
    setBusy(true);
    let next = attachments;
    for (const file of Array.from(list)) {
      const problem = checkFile(file);
      if (problem) {
        notify.error("File not attached", problem);
      } else if (next.length >= MAX_FILES) {
        notify.error("File not attached", `A complaint can have at most ${MAX_FILES} files.`);
      } else {
        const sent = await uploadFile(complaintId, withKnownType(file));
        if (sent.ok) next = [...next, sent.data];
        else notify.error("File not attached", `${file.name}: ${sent.message}`);
      }
    }
    onChange(next);
    setBusy(false);
  }

  async function remove(file: PortalAttachment) {
    setBusy(true);
    const result = await removeFile(complaintId, file.id);
    setBusy(false);
    if (!result.ok) return notify.error("File not removed", result.message);
    onChange(attachments.filter((a) => a.id !== file.id));
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className={eyebrow}>Files you added ({attachments.length})</p>
        {editable && (
          <>
            <button
              type="button"
              disabled={busy || attachments.length >= MAX_FILES}
              onClick={() => input.current?.click()}
              className="focus-ring inline-flex h-[2.1rem] cursor-pointer items-center gap-1.5 rounded-full border-[1.5px] border-[#E5E7EB] bg-white px-3.5 text-[0.78rem] font-bold text-slate-ink transition-colors hover:border-crimson hover:text-crimson disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Icon name="attach" size={14} />
              {busy ? "Working…" : "Add files"}
            </button>
            <input
              ref={input}
              type="file"
              multiple
              accept={ACCEPT}
              className="sr-only"
              tabIndex={-1}
              aria-label="Choose files to add"
              onChange={(e) => {
                if (e.target.files?.length) void add(e.target.files);
                e.target.value = "";
              }}
            />
          </>
        )}
      </div>

      {attachments.length === 0 ? (
        <p className={`mt-2 ${muted}`}>No files yet.</p>
      ) : (
        <ul className="m-0 mt-2.5 grid list-none grid-cols-[repeat(auto-fill,minmax(8.5rem,1fr))] gap-2.5 p-0">
          {attachments.map((a) => (
            <li key={a.id} className="group relative overflow-hidden rounded-[1rem] bg-[#f7f4f5]">
              <a
                href={fileUrl(complaintId, a.id)}
                target="_blank"
                rel="noopener"
                aria-label={`Open ${a.fileName}`}
                className="focus-ring flex flex-col"
              >
                {isImage(a.mimeType) ? (
                  // eslint-disable-next-line @next/next/no-img-element -- the person's own upload, served by the API
                  <img src={fileUrl(complaintId, a.id)} alt={a.fileName} loading="lazy" className="aspect-[4/3] w-full object-cover" />
                ) : (
                  <span className="grid aspect-[4/3] w-full place-items-center bg-white text-crimson">
                    <Icon name="file" size={28} />
                  </span>
                )}
                <span className="block px-2.5 py-2">
                  <span className="block truncate text-[0.76rem] font-bold text-ink">{a.fileName}</span>
                  <span className="block text-[0.68rem] text-muted">{formatSize(a.sizeBytes)}</span>
                </span>
              </a>
              {editable && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void remove(a)}
                  aria-label={`Remove ${a.fileName}`}
                  className="focus-ring absolute right-1.5 top-1.5 grid size-7 cursor-pointer place-items-center rounded-full border-0 bg-white/95 text-slate-muted shadow-[0_2px_8px_rgba(0,0,0,0.2)] transition-colors hover:text-crimson disabled:cursor-not-allowed"
                >
                  <Icon name="close" size={13} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
