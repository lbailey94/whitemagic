import { PageHeader } from "@/components/PageHeader";
import { ContactForm } from "@/components/ContactForm";
import Link from "next/link";
import { Mail, Calendar, Boxes } from "lucide-react";

export const metadata = {
  title: "Contact — WhiteMagic",
  description:
    "Get in touch about WhiteMagic — deployment help, integration, enterprise, or just to say it helped.",
};

// Cal.com to be configured — for now, direct email booking.
const BOOKING_URL = "mailto:whitemagicdev@proton.me?subject=WhiteMagic%20Discovery%20Call&body=Hi%20there%2C%0A%0AI'd%20like%20to%20schedule%20a%2030-minute%20discovery%20call.%0A%0AHere's%20what%20I'm%20working%20on%3A%0A%0A";
const EMAIL = "whitemagicdev@proton.me";

export default function ContactPage() {
  return (
    <>
      <PageHeader
        eyebrow="Contact"
        title="Let's talk."
        lede="Questions about deployment, integration, or enterprise use? Email directly — no forms, no funnels, no sales pipeline."
      />

      <section className="container-site py-16">
        <div className="mx-auto grid max-w-3xl gap-6 md:grid-cols-2">
          <ContactCard
            icon={Calendar}
            title="Book a call"
            body="Send an email to request a 30-minute discovery call. I'll reply with availability and a video link within one business day."
            cta="Request a call"
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
            Plain form. Goes to the same inbox, no ceremony. I reply within
            two business days.
          </p>
          <ContactForm />
        </div>

        <div className="mx-auto mt-10 max-w-3xl rounded-2xl border border-border bg-surface-alt p-8">
          <div className="flex items-start gap-4">
            <Boxes className="mt-1 h-5 w-5 shrink-0 text-lavender" />
            <div>
              <h3 className="mb-1 font-head text-lg font-semibold text-ink">
                Want to see the work first?
              </h3>
              <p className="mb-3 text-muted">
                WhiteMagic is MIT-licensed. Explore the open-source work and
                research right here on the site before reaching out — that&apos;s
                encouraged.
              </p>
              <Link
                href="/open-source"
                className="inline-flex items-center gap-2 text-sm font-medium text-lavender hover:text-lavender-dark"
              >
                Explore the open source →
              </Link>
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
