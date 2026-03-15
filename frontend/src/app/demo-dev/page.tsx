"use client";

import DemoAnimation from "@/components/DemoAnimation";

export default function DemoDevPage() {
  return (
    <div className="min-h-screen overflow-hidden">
      <DemoAnimation autoStart={false} showControls={true} />
    </div>
  );
}