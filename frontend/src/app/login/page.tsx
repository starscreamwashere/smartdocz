import { redirect } from "next/navigation";

// Doc-friendly alias (App Flow uses /login) → Clerk's sign-in route.
export default function LoginAlias() {
  redirect("/sign-in");
}
