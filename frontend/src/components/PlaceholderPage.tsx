import Link from "next/link";

export function PlaceholderPage({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-8 text-center">
      <h1 className="text-3xl font-extrabold tracking-[-0.02em] text-slate-ink">
        {title}
      </h1>
      <p className="max-w-md text-slate-muted">{text}</p>
      <Link
        href="/"
        className="font-bold text-crimson hover:text-crimson-link-hover hover:underline"
      >
        Back to sign in
      </Link>
    </main>
  );
}
