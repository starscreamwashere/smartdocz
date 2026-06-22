import { redirect } from "next/navigation";

// Doc-friendly alias (App Flow uses /signup) → Clerk's sign-up route.
export default function SignupAlias() {
  redirect("/sign-up");
}
