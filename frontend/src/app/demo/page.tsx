"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DemoAnimationV2 from "@/components/DemoAnimationV2";

function DemoContent() {
  const searchParams = useSearchParams();
  const showControls = searchParams.get("controls") !== "0";

  return (
    <div className="min-h-screen">
      <DemoAnimationV2 autoStart showControls={showControls} />
    </div>
  );
}

export default function DemoPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e27]">
        <div className="text-white/50">Loading world-class demo…</div>
      </div>
    }>
      <DemoContent />
    </Suspense>
  );
}
