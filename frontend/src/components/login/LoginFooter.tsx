"use client";

import { useEffect, useState } from "react";

export function LoginFooter() {
  const [year, setYear] = useState(2026);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setYear(new Date().getFullYear());
  }, []);

  return (
    <p className="m-0 text-center text-[0.74rem] text-[#8A909B]">
      Need help? Contact the SPRPTA office. &copy; {year} SPRPTA
    </p>
  );
}
