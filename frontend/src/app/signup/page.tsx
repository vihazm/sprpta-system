import { SignUpFlow } from "@/components/signup/SignUpFlow";
import { SignUpPanel } from "@/components/signup/SignUpPanel";

export const metadata = { title: "Create account | SPRPTA" };

// Complainant sign-up: what happens to a complaint on the left, the form and the one-time code on the right.
export default function SignUpPage() {
  return (
    <main className="grid min-h-dvh bg-page min-[900px]:grid-cols-[1fr_1.1fr]">
      <SignUpPanel />
      <section className="flex items-center justify-center px-[2rem] py-[2.5rem] max-[599px]:px-[1rem]">
        <SignUpFlow />
      </section>
    </main>
  );
}
