"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

// Sri Lankan buses, three-wheelers and passengers. Swap or add entries here.
const STRIPS = [
  { src: "/images/login/tuk-red-road.jpg", pos: "64% 62%" },
  { src: "/images/login/bus-inside.jpg", pos: "50% 38%" },
  { src: "/images/login/bus-blue.jpg", pos: "80% 50%" },
  { src: "/images/login/tuk-green-night.jpg", pos: "38% 58%" },
  { src: "/images/login/bus-painted.jpg", pos: "24% 60%", zoom: 1.6 },
  { src: "/images/login/tuk-red-park.jpg", pos: "46% 62%" },
] as const;

export function PhotoStrips() {
  const [active, setActive] = useState(0);
  const paused = useRef(false);

  // rotate on their own until the pointer arrives; honour reduced motion
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => {
      if (!paused.current) setActive((a) => (a + 1) % STRIPS.length);
    }, 3600);
    return () => clearInterval(id);
  }, []);

  return (
    <section
      aria-hidden="true"
      onMouseLeave={() => {
        paused.current = false;
      }}
      className="relative order-2 mx-3 mb-3 flex h-[17rem] gap-2 min-[900px]:order-none min-[900px]:my-[0.8rem] min-[900px]:ml-0 min-[900px]:mr-[0.8rem] min-[900px]:h-auto min-[900px]:min-h-[calc(100dvh-1.6rem)] min-[900px]:gap-[0.5rem]"
    >
      {STRIPS.map((s, k) => {
        const on = k === active;
        return (
          <div
            key={s.src}
            onMouseEnter={() => {
              paused.current = true;
              setActive(k);
            }}
            onClick={() => setActive(k)}
            style={{ flexGrow: on ? 6 : 1, flexBasis: 0 }}
            className="relative min-w-0 cursor-pointer overflow-hidden rounded-[1.5rem] bg-[#3b1a22] transition-[flex-grow] duration-[900ms] ease-[cubic-bezier(.2,.8,.2,1)]"
          >
            <Image
              src={s.src}
              alt=""
              fill
              priority={k === 0}
              sizes="(min-width: 900px) 40vw, 100vw"
              quality={85}
              className="object-cover"
              style={{
                objectPosition: s.pos,
                ...("zoom" in s
                  ? { transform: `scale(${s.zoom})`, transformOrigin: s.pos }
                  : {}),
              }}
            />
            {/* crimson wash on closed strips */}
            <div
              className={`absolute inset-0 bg-gradient-to-b from-[rgba(176,16,47,0.42)] to-[rgba(110,8,30,0.68)] transition-opacity duration-700 ${
                on ? "opacity-0" : "opacity-100"
              }`}
            />
            {/* bottom shade behind the headline on the open strip */}
            <div
              className={`absolute inset-0 bg-[linear-gradient(to_top,rgba(96,6,26,0.78)_0%,rgba(96,6,26,0.15)_45%,transparent_70%)] transition-opacity duration-700 ${
                on ? "opacity-100" : "opacity-0"
              }`}
            />
          </div>
        );
      })}
      <p className="pointer-events-none absolute bottom-[1.1rem] left-[1.2rem] right-[1.2rem] z-10 max-w-[11em] font-display text-[1.6rem] leading-[1.02] tracking-[-0.035em] text-white [text-shadow:0_2px_24px_rgba(60,0,15,0.45)] min-[900px]:bottom-8 min-[900px]:left-[2.2rem] min-[900px]:right-[2.2rem] min-[900px]:text-[clamp(1.9rem,3.1vw,3.1rem)]">
        A fairer ride starts with your word.
      </p>
    </section>
  );
}
