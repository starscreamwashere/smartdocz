import { redirect } from "next/navigation";

// The app's first screen is /home (App Flow doc, §4).
export default function RootPage() {
  redirect("/home");
}
