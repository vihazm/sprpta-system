import { AccountBackdrop } from "@/components/signup/AccountBackdrop";
import { ResetPasswordFlow } from "@/components/signup/ResetPasswordFlow";

export const metadata = { title: "Forgot password | SPRPTA" };

export default function ForgotPasswordPage() {
  return (
    <AccountBackdrop>
      <div className="w-full max-w-[32rem] overflow-hidden rounded-[2.1rem] bg-white shadow-[0_50px_100px_-40px_rgba(20,0,8,0.85),0_0_0_1px_rgba(255,255,255,0.25)]">
        <ResetPasswordFlow />
      </div>
    </AccountBackdrop>
  );
}
