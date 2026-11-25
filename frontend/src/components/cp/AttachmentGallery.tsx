"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/dashboard/icons";
import { muted } from "@/components/dashboard/ui";
import { notify } from "@/lib/notify";
import { fileUrl, removeFile, uploadFile } from "./api";
import { ACCEPT, MAX_FILES, checkFile, formatSize, isImage, withKnownType } from "./files";
import type { PortalAttachment } from "./types";

/**
 * The files of one complaint. A photo shows as a large picture that opens bigger in this page, any other file as a
 * card that opens in a new tab. While SPRPTA has not started on the complaint, files can still be added or removed.
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
  const [viewing, setViewing] = useState<number | null>(null); // the id of the photo shown large

  const photos = attachments.filter((a) => isImage(a.mimeType));

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
    <div className="flex flex-col gap-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className={`m-0 ${muted}`}>
          {attachments.length === 0
            ? "No files added."
            : `${attachments.length} ${attachments.length === 1 ? "file" : "files"} added. Select a photo to see it larger.`}
        </p>
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

      {attachments.length > 0 && (
        <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(13rem,1fr))] gap-3.5 p-0">
          {attachments.map((a) => {
            const photo = isImage(a.mimeType);
            const body = (
              <>
                {photo ? (
                  // eslint-disable-next-line @next/next/no-img-element -- the person's own upload, served by the API
                  <img
                    src={fileUrl(complaintId, a.id)}
                    alt={a.fileName}
                    loading="lazy"
                    className="aspect-[4/3] w-full object-cover transition-transform duration-200 group-hover:scale-[1.03]"
                  />
                ) : (
                  <span className="grid aspect-[4/3] w-full place-items-center bg-[#fbeff2] text-crimson">
                    <Icon name="file" size={34} />
                  </span>
                )}
                <span className="block px-3 py-2.5">
                  <span className="block truncate text-[0.82rem] font-bold text-ink">{a.fileName}</span>
                  <span className="block text-[0.72rem] text-muted">{formatSize(a.sizeBytes)}</span>
                </span>
              </>
            );
            const frame =
              "focus-ring group flex w-full cursor-pointer flex-col overflow-hidden rounded-[1.1rem] border-0 bg-[#f7f4f5] p-0 text-left";
            return (
              <li key={a.id} className="relative">
                {photo ? (
                  <button type="button" aria-label={`View ${a.fileName} larger`} onClick={() => setViewing(a.id)} className={frame}>
                    {body}
                  </button>
                ) : (
                  <a href={fileUrl(complaintId, a.id)} target="_blank" rel="noopener" aria-label={`Open ${a.fileName}`} className={frame}>
                    {body}
                  </a>
                )}
                {editable && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void remove(a)}
                    aria-label={`Remove ${a.fileName}`}
                    className="focus-ring absolute right-2 top-2 grid size-8 cursor-pointer place-items-center rounded-full border-0 bg-white/95 text-slate-muted shadow-[0_2px_8px_rgba(0,0,0,0.25)] transition-colors hover:text-crimson disabled:cursor-not-allowed"
                  >
                    <Icon name="close" size={14} />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {viewing !== null && (
        <PhotoViewer complaintId={complaintId} photos={photos} startId={viewing} onClose={() => setViewing(null)} />
      )}
    </div>
  );
}

/** A photo shown large over the page, with the arrow keys or buttons to move between the photos of the complaint. */
function PhotoViewer({
  complaintId,
  photos,
  startId,
  onClose,
}: {
  complaintId: number;
  photos: PortalAttachment[];
  startId: number;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [index, setIndex] = useState(Math.max(0, photos.findIndex((p) => p.id === startId)));
  const photo = photos[index];

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  function step(by: number) {
    setIndex((i) => (i + by + photos.length) % photos.length);
  }

  if (!photo) return null;
  const nav =
    "focus-ring absolute top-1/2 grid size-11 -translate-y-1/2 cursor-pointer place-items-center rounded-full border-0 bg-white/90 text-ink shadow-[0_4px_16px_rgba(0,0,0,0.35)] transition-colors hover:bg-white";

  return (
    <dialog
      ref={dialog}
      aria-label={photo.fileName}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialog.current) onClose(); // a click on the dark area around the photo
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowRight") step(1);
        else if (e.key === "ArrowLeft") step(-1);
      }}
      className="m-auto w-[min(70rem,calc(100vw-1.5rem))] max-w-none overflow-visible rounded-[1.5rem] bg-transparent p-0 text-white backdrop:bg-[rgba(20,4,10,0.82)]"
    >
      <div className="relative flex flex-col items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element -- the person's own upload, served by the API */}
        <img
          src={fileUrl(complaintId, photo.id)}
          alt={photo.fileName}
          className="max-h-[calc(100dvh-9rem)] max-w-full rounded-[1.2rem] bg-black/30 object-contain shadow-[0_30px_80px_-20px_rgba(0,0,0,0.7)]"
        />
        {photos.length > 1 && (
          <>
            <button type="button" aria-label="Previous photo" onClick={() => step(-1)} className={`${nav} left-3`}>
              <Icon name="prev" size={20} />
            </button>
            <button type="button" aria-label="Next photo" onClick={() => step(1)} className={`${nav} right-3`}>
              <Icon name="next" size={20} />
            </button>
          </>
        )}
        <div className="flex w-full flex-wrap items-center justify-between gap-3 px-1">
          <p className="m-0 min-w-0 text-[0.85rem] font-bold">
            <span className="block truncate">{photo.fileName}</span>
            <span className="text-[0.74rem] font-medium text-white/75">
              {formatSize(photo.sizeBytes)}
              {photos.length > 1 && ` · ${index + 1} of ${photos.length}`}
            </span>
          </p>
          <div className="flex gap-2">
            <a
              href={fileUrl(complaintId, photo.id)}
              target="_blank"
              rel="noopener"
              className="focus-ring inline-flex h-[2.3rem] items-center rounded-full bg-white/15 px-4 text-[0.8rem] font-bold text-white transition-colors hover:bg-white/25"
            >
              Open original
            </a>
            <button
              type="button"
              onClick={onClose}
              className="focus-ring inline-flex h-[2.3rem] cursor-pointer items-center rounded-full border-0 bg-white px-4 text-[0.8rem] font-extrabold text-ink"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </dialog>
  );
}
