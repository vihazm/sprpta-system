"use client";

import { useRef, useState, type DragEvent } from "react";
import { Icon } from "@/components/dashboard/icons";
import { muted } from "@/components/dashboard/ui";
import { ACCEPT, ACCEPTED_TEXT, MAX_FILES, checkFile, formatSize, isImage } from "./files";

/** A file chosen on the form but not uploaded yet. `preview` is a temporary address for showing a photo. */
export type PickedFile = { file: File; preview: string | null };

/** Frees the temporary preview addresses of files that are no longer shown. */
export function releasePreviews(files: PickedFile[]) {
  files.forEach((f) => f.preview && URL.revokeObjectURL(f.preview));
}

/**
 * Choose files for a complaint: press the button, or drop them here. A photo shows a small preview, every file can be
 * taken out again before sending. Files that cannot be attached are named, with the reason, and left out.
 */
export function EvidencePicker({
  picked,
  onChange,
  disabled,
}: {
  picked: PickedFile[];
  onChange: (next: PickedFile[]) => void;
  disabled: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);

  function add(list: FileList | File[]) {
    const accepted: PickedFile[] = [];
    const refused: string[] = [];
    for (const file of Array.from(list)) {
      const problem = checkFile(file);
      if (problem) refused.push(problem);
      else if (picked.length + accepted.length >= MAX_FILES) {
        refused.push(`${file.name}: a complaint can have at most ${MAX_FILES} files.`);
      } else accepted.push({ file, preview: isImage(file.type) ? URL.createObjectURL(file) : null });
    }
    setProblems(refused);
    if (accepted.length) onChange([...picked, ...accepted]);
  }

  function remove(index: number) {
    releasePreviews([picked[index]]);
    onChange(picked.filter((_, i) => i !== index));
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setOver(false);
    if (!disabled) add(e.dataTransfer.files);
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        className={`flex flex-wrap items-center justify-between gap-3 rounded-[1.25rem] border-2 border-dashed px-5 py-4 transition-colors ${
          over ? "border-crimson bg-[#fbeff2]" : "border-[#d9c9cd] bg-[#faf7f8]"
        }`}
      >
        <div className="min-w-0">
          <p className="m-0 text-[0.88rem] font-extrabold">Add photos or documents</p>
          <p className={`m-0 mt-0.5 ${muted}`}>
            Drop files here or choose them. {ACCEPTED_TEXT}. Up to {MAX_FILES} files.
          </p>
        </div>
        <button
          type="button"
          disabled={disabled || picked.length >= MAX_FILES}
          onClick={() => input.current?.click()}
          className="focus-ring inline-flex h-[2.6rem] cursor-pointer items-center gap-2 rounded-[0.9rem] bg-white px-4 text-[0.85rem] font-bold text-slate-ink shadow-[0_0_0_1px_rgba(60,20,30,0.1)] transition-colors hover:bg-field disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Icon name="attach" size={16} />
          Choose files
        </button>
        <input
          ref={input}
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          tabIndex={-1}
          aria-label="Choose files to attach"
          onChange={(e) => {
            if (e.target.files) add(e.target.files);
            e.target.value = ""; // so the same file can be chosen again after it was taken out
          }}
        />
      </div>

      {problems.length > 0 && (
        <ul role="alert" className="m-0 flex list-none flex-col gap-1 p-0 text-[0.78rem] font-semibold text-error">
          {problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}

      {picked.length > 0 && (
        <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(13rem,1fr))] gap-2.5 p-0">
          {picked.map((p, i) => (
            <li key={`${p.file.name}-${i}`} className="flex items-center gap-3 rounded-[1rem] bg-[#f7f4f5] p-2.5">
              {p.preview ? (
                // eslint-disable-next-line @next/next/no-img-element -- a temporary preview of a file on this computer
                <img src={p.preview} alt="" className="size-[2.9rem] flex-none rounded-[0.7rem] object-cover" />
              ) : (
                <span className="grid size-[2.9rem] flex-none place-items-center rounded-[0.7rem] bg-white text-crimson">
                  <Icon name="file" size={20} />
                </span>
              )}
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[0.82rem] font-bold">{p.file.name}</span>
                <span className={`block ${muted}`}>{formatSize(p.file.size)}</span>
              </span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => remove(i)}
                aria-label={`Remove ${p.file.name}`}
                className="focus-ring grid size-8 flex-none cursor-pointer place-items-center rounded-full border-0 bg-white text-slate-muted transition-colors hover:text-crimson disabled:cursor-not-allowed"
              >
                <Icon name="close" size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
