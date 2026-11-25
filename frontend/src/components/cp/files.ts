// What a complainant may attach. It follows the backend's list (complaint_attachment_service.py), which is the
// real check: images, PDFs, audio, video, plain text and emails. Anything else, such as programs or web pages,
// is refused so that an uploaded file can never run anything.

const MB = 1024 * 1024;

/** File extension to the type the backend expects, for the browsers that report no type (for example for .eml). */
const BY_EXTENSION: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  pdf: "application/pdf",
  txt: "text/plain",
  eml: "message/rfc822",
  mp3: "audio/mpeg",
  m4a: "audio/mp4",
  wav: "audio/wav",
  ogg: "audio/ogg",
  mp4: "video/mp4",
  webm: "video/webm",
  mov: "video/quicktime",
};

const ALLOWED = new Set([...Object.values(BY_EXTENSION), "audio/x-m4a", "audio/x-wav"]);

export const MAX_FILES = 10;
export const ACCEPT = Object.keys(BY_EXTENSION)
  .map((ext) => `.${ext}`)
  .join(",");
export const ACCEPTED_TEXT = "Photos (JPG, PNG, WebP), PDF, audio, video, text or email files";

function typeOf(file: File): string {
  if (ALLOWED.has(file.type)) return file.type;
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  return BY_EXTENSION[ext] ?? file.type;
}

function limitOf(type: string): number {
  return type.startsWith("video/") ? 50 * MB : type.startsWith("audio/") ? 25 * MB : 10 * MB;
}

/** A readable reason the file cannot be attached, or an empty string when it can. */
export function checkFile(file: File): string {
  const type = typeOf(file);
  if (!ALLOWED.has(type)) return `${file.name}: this kind of file cannot be attached.`;
  if (file.size === 0) return `${file.name}: the file is empty.`;
  if (file.size > limitOf(type)) return `${file.name}: it is larger than ${limitOf(type) / MB} MB.`;
  return "";
}

/** The file with the type the server expects, so a file the browser could not name is still accepted. */
export function withKnownType(file: File): File {
  const type = typeOf(file);
  return type === file.type ? file : new File([file], file.name, { type });
}

export const isImage = (mimeType: string) => mimeType.startsWith("image/");

/** "84 KB", "2.4 MB". */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < MB) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / MB).toFixed(1)} MB`;
}
