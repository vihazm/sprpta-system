import { AccountBackdrop } from "@/components/signup/AccountBackdrop";
import { SignUpFlow } from "@/components/signup/SignUpFlow";
import { SignUpPanel } from "@/components/signup/SignUpPanel";

export const metadata = { title: "Create account | SPRPTA" };

// Complainant sign-up: one card on the blurred login photo, with what happens to a complaint on the crimson half
// and the form and the one-time code on the white half.
export default function SignUpPage() {
  return (
    <AccountBackdrop>
      <div className="grid w-full max-w-[66rem] overflow-hidden rounded-[2.1rem] bg-white shadow-[0_50px_100px_-40px_rgba(20,0,8,0.85),0_0_0_1px_rgba(255,255,255,0.25)] min-[900px]:grid-cols-[1fr_1.08fr]">
        <SignUpPanel />
        <SignUpFlow />
      </div>
    </AccountBackdrop>
  );
}
