/** Always rendered so screen readers announce changes (aria-live). */
export function FieldError({ id, message }: { id: string; message: string }) {
  return (
    <div id={id} aria-live="polite">
      {message && (
        <div className="flex items-start gap-[0.35rem] text-[0.8rem] font-semibold leading-[1.35] text-error">
          <span
            aria-hidden="true"
            className="mt-[0.05rem] grid h-4 w-4 flex-none place-items-center rounded-full bg-error text-[0.68rem] text-white"
          >
            !
          </span>
          <span>{message}</span>
        </div>
      )}
    </div>
  );
}
