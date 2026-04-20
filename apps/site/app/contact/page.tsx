import { PageHeader } from "@/components/PageHeader";
import { ContactForm } from "@/components/ContactForm";
import { Mail, Calendar, Github } from "lucide-react";

export const metadata = {
  title: "Contact — WhiteMagic Labs",
  description:
    "Book a discovery call or reach out directly. 30-minute conversation, no pitch deck.",
};

// TODO: replace with real Cal.com or Calendly URL once configured.
const BOOKING_URL = "https://cal.com/whitemagic-labs";
const EMAIL = "whitemagicdev@proton.me";
const GITHUB = "https://github.com/whitemagic-ai";

export default function ContactPage() {
  return (
    <>
      <PageHeader
        eyebrow="Contact"
        title="Let's talk."
        lede="Thirty-minute discovery call. No deck, no pitch — a real conversation about what you're building and whether I'm the right person to help."
      />

      <section className="container-site py-16">
        <div className="mx-auto grid max-w-3xl gap-6 md:grid-cols-2">
          <ContactCard
            icon={Calendar}
            title="Book a call"
            body="Pick a 30-minute slot that works. You'll get a calendar invite with a video link and a short form to prep me on what you're working on."
            cta="Open booking"
            href={BOOKING_URL}
          />
          <ContactCard
            icon={Mail}
            title="Email"
            body="Prefer writing? Send a message with what you're trying to build, any constraints, and I'll reply within two business days."
            cta={EMAIL}
            href={`mailto:${EMAIL}`}
          />
        </div>

        <div className="mx-auto mt-10 max-w-3xl">
          <h2 className="mb-1 font-head text-2xl font-semibold text-ink">
            Or send a message
          </h2>
          <p className="mb-6 text-sm text-muted">
            Plain form. Goes to the same inbox, no ceremony. Lucas replies
            within two business days.
          </p>
          <ContactForm />
        </div>

        <div className="mx-auto mt-10 max-w-3xl rounded-2xl border border-border bg-surface-alt p-8">
          <div className="flex items-start gap-4">
            <Github className="mt-1 h-5 w-5 shrink-0 text-lavender" />
            <div>
              <h3 className="mb-1 font-head text-lg font-semibold text-ink">
                Want to see the work first?
              </h3>
              <p className="mb-3 text-muted">
                WhiteMagic is MIT-licensed and public. If you&apos;d like
                to read the code before reaching out — that&apos;s
                encouraged.
              </p>
              <a
                href={GITHUB}
                className="inline-flex items-center gap-2 text-sm font-medium text-lavender hover:text-lavender-dark"
              >
                github.com/whitemagic-ai →
              </a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function ContactCard({
  icon: Icon,
  title,
  body,
  cta,
  href,
}: {
  icon: typeof Mail;
  title: string;
  body: string;
  cta: string;
  href: string;
}) {
  return (
    <a
      href={href}
      target={href.startsWith("http") ? "_blank" : undefined}
      rel={href.startsWith("http") ? "noreferrer" : undefined}
      className="group flex flex-col rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender hover:bg-lavender-bg"
    >
      <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-lavender-bg text-lavender">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="mb-2 font-head text-xl font-semibold text-ink">
        {title}
      </h3>
      <p className="mb-6 flex-1 text-sm leading-relaxed text-muted">{body}</p>
      <span className="font-mono text-xs uppercase tracking-wider text-lavender transition group-hover:text-lavender-dark">
        {cta} →
      </span>
    </a>
  );
}
