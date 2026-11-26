import Image from "next/image";
import type { ReactNode } from "react";
import { LOGIN_BACKDROP } from "@/components/login/backdrop";

// The page behind the complainant's account screens: the login photo, blurred and tinted crimson, with the card
// in the middle and the authority's name under it.
export function AccountBackdrop({ children }: { children: ReactNode }) {
  return (
    <main className="relative isolate flex min-h-dvh flex-col items-center justify-center gap-[1.3rem] overflow-hidden bg-[#3a0a16] px-[2rem] py-[2.5rem] max-[899px]:px-[0.9rem] max-[899px]:py-[1.2rem]">
      <div aria-hidden="true" className="absolute inset-0 -z-10">
        <Image
          src={LOGIN_BACKDROP}
          alt=""
          fill
          priority
          sizes="100vw"
          quality={80}
          className="scale-110 object-cover blur-[8px]"
          style={{ objectPosition: "46% 62%" }}
        />
        <div className="absolute inset-0 bg-[linear-gradient(110deg,rgba(90,6,26,0.72),rgba(60,8,22,0.45))]" />
      </div>

      {children}

      <p className="m-0 text-center text-[0.78rem] text-white/80">
        Southern Provincial Road Passenger Transport Authority · Galle, Matara and Hambantota
      </p>
    </main>
  );
}
