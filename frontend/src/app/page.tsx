import Image from "next/image";
import { BenefitsBento } from "@/components/login/BenefitsBento";
import { BrandHeader } from "@/components/login/BrandHeader";
import { LoginFooter } from "@/components/login/LoginFooter";
import { LoginSheet } from "@/components/login/LoginSheet";
import { LOGIN_BACKDROP } from "@/components/login/backdrop";

// Common sign-in page for every role; also the landing page of the system.
// Login card on the left; the photo flows in from the right behind a crimson wave.
export default function Home() {
  return (
    <main className="relative isolate min-h-dvh overflow-hidden bg-[#fbf8f9]">
      {/* clip shape for the wavy photo edge */}
      <svg width="0" height="0" aria-hidden="true" className="absolute">
        <defs>
          <clipPath id="photo-wave" clipPathUnits="objectBoundingBox">
            <path d="M0.17,0 C0.05,0.16 0.25,0.33 0.12,0.5 C0.02,0.66 0.2,0.83 0.08,1 L1,1 L1,0 Z" />
          </clipPath>
        </defs>
      </svg>

      {/* soft crimson glow behind the form */}
      <div
        aria-hidden="true"
        className="absolute -left-[12rem] -top-[10rem] -z-10 h-[40rem] w-[40rem] rounded-full bg-[radial-gradient(circle,rgba(179,17,47,0.11),transparent_65%)]"
      />

      {/* desktop photo panel */}
      <div aria-hidden="true" className="absolute inset-y-0 right-0 hidden w-[60%] min-[900px]:block">
        <div
          className="absolute inset-0 -translate-x-[4.5%] bg-[#A8102F]"
          style={{ clipPath: "url(#photo-wave)" }}
        />
        <div className="absolute inset-0" style={{ clipPath: "url(#photo-wave)" }}>
          <Image
            src={LOGIN_BACKDROP}
            alt=""
            fill
            priority
            sizes="60vw"
            quality={85}
            className="object-cover"
            style={{ objectPosition: "46% 62%" }}
          />
          <div className="absolute inset-0 bg-[linear-gradient(to_top,rgba(96,6,26,0.9)_0%,rgba(96,6,26,0.5)_42%,rgba(40,6,16,0.14)_72%,rgba(40,6,16,0.3)_100%)]" />
          <div className="absolute bottom-[2.6rem] left-[18%] right-[7%] flex flex-col gap-[1rem] text-white">
            <h2 className="m-0 max-w-[13em] font-display text-[clamp(1.9rem,3.2vw,3.2rem)] leading-[1.03] tracking-[-0.035em] [text-shadow:0_2px_26px_rgba(20,0,8,0.5)]">
              A fairer ride starts with your word.
            </h2>
            <BenefitsBento />
          </div>
        </div>
      </div>

      {/* form column */}
      <section className="relative z-10 flex min-h-dvh flex-col px-[2.6rem] pb-[1.2rem] pt-6 max-[899px]:px-[1.1rem] max-[899px]:pt-[1.2rem] min-[900px]:w-[44%]">
        <BrandHeader />
        <div className="flex flex-1 items-center justify-center py-4 max-[899px]:py-[1.2rem]">
          <LoginSheet />
        </div>
        <LoginFooter />
      </section>

      {/* phone photo band */}
      <div className="relative h-[19rem] overflow-hidden min-[900px]:hidden" aria-hidden="true">
        <Image
          src={LOGIN_BACKDROP}
          alt=""
          fill
          sizes="100vw"
          quality={80}
          className="object-cover"
          style={{ objectPosition: "50% 66%" }}
        />
        <div className="absolute inset-0 bg-[linear-gradient(to_top,rgba(96,6,26,0.9)_0%,rgba(96,6,26,0.35)_50%,rgba(40,6,16,0.2)_100%)]" />
        <p className="absolute bottom-[1.2rem] left-[1.1rem] right-[1.1rem] m-0 font-display text-[1.7rem] leading-[1.05] tracking-[-0.03em] text-white">
          A fairer ride starts with your word.
        </p>
      </div>
    </main>
  );
}
