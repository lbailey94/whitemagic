import { redirect } from "next/navigation";

export const metadata = {
  title: "Prescience — WhiteMagic Labs",
  description: "What we saw before the market.",
};

export default function PresciencePage() {
  redirect("/timeline#prescience");
}
