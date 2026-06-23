import { Suspense } from "react";

import { ChatWorkspace } from "@/components/chat-workspace";

export default function ChatPage() {
  // ChatWorkspace reads the active session from the URL via useSearchParams,
  // which requires a Suspense boundary in the App Router.
  return (
    <Suspense fallback={null}>
      <ChatWorkspace />
    </Suspense>
  );
}
