import Image from "next/image";
import { LOGIN_BACKDROP } from "@/components/login/backdrop";
import { SignUpFlow } from "@/components/signup/SignUpFlow";
import { SignUpPanel } from "@/components/signup/SignUpPanel";

export const metadata = { title: "Create account | SPRPTA" };

// Complainant sign-up: the login photo, blurred and tinted crimson, fills the page. One card sits on it: what
// happens to a complaint on the crimson half, the form and the one-time code on the white half.
export default function SignUpPage() {
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

      <div className="grid w-full max-w-[66rem] overflow-hidden rounded-[2.1rem] bg-white shadow-[0_50px_100px_-40px_rgba(20,0,8,0.85),0_0_0_1px_rgba(255,255,255,0.25)] min-[900px]:grid-cols-[1fr_1.08fr]">
        <SignUpPanel />
        <SignUpFlow />
      </div>

      <p className="m-0 text-center text-[0.78rem] text-white/80">
        Southern Provincial Road Passenger Transport Authority · Galle, Matara and Hambantota
      </p>
    </main>
  );
}
