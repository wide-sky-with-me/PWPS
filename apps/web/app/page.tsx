"use client";

import { useState } from "react";
import { GuidedWorkbench } from "@/components/guided-workbench";
import { HistoryPage } from "@/components/history-page";
import { SettingsPage } from "@/components/settings-page";

type Page = "workbench" | "history" | "settings";

export default function Home() {
  const [page, setPage] = useState<Page>("workbench");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  function handleViewRun(runId: string) {
    setSelectedRunId(runId);
    setPage("workbench");
  }

  switch (page) {
    case "history":
      return (
        <HistoryPage
          onBack={() => setPage("workbench")}
          onViewRun={handleViewRun}
        />
      );
    case "settings":
      return <SettingsPage onBack={() => setPage("workbench")} />;
    default:
      return (
        <GuidedWorkbench
          onShowHistory={() => setPage("history")}
          onShowSettings={() => setPage("settings")}
          initialRunId={selectedRunId}
        />
      );
  }
}
