import { redirect } from "next/navigation";

export const metadata = {
  title: "Agent Governance — WhiteMagic Labs",
  description: "Runtime governance for AI agents.",
};

export default function GovernancePage() {
  redirect("/economy#governance");
}
