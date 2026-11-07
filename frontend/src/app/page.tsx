import { BrandHeader } from "@/components/login/BrandHeader";
import { LoginFooter } from "@/components/login/LoginFooter";
import { LoginSheet } from "@/components/login/LoginSheet";
import { PhotoStrips } from "@/components/login/PhotoStrips";

// Common sign-in page for every role; also the landing page of the system.
export default function Home() {
  return (
    <main className="grid min-h-dvh bg-page min-[900px]:grid-cols-[minmax(24rem,1fr)_minmax(0,1.3fr)]">
      <section className="flex flex-col px-[2.6rem] pb-[1.2rem] pt-6 max-[899px]:px-[1.1rem] max-[899px]:pt-[1.2rem]">
        <BrandHeader />
        <div className="flex flex-1 items-center justify-center py-4 max-[899px]:py-[1.2rem]">
          <LoginSheet />
        </div>
        <LoginFooter />
      </section>
      <PhotoStrips />
    </main>
  );
}
