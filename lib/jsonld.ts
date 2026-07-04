/**
 * schema.org JSON-LD builders.
 *
 * Emitted via a tiny <JsonLd> component (see components/JsonLd.tsx).
 * Each builder returns a plain object; callers wrap it in the component.
 */
import { SERVICES, type ServiceSlug } from "./data/services";

const SITE_URL = "https://whitemagic.dev";
const ORG_NAME = "WhiteMagic";
const ORG_LEGAL = "WhiteMagic";

/** Root organization node, referenced by other nodes via @id. */
export function organizationLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": `${SITE_URL}/#org`,
    name: ORG_NAME,
    legalName: ORG_LEGAL,
    url: SITE_URL,
    logo: `${SITE_URL}/opengraph-image`,
    description:
      "Cognitive operating system for AI agents — 614 callable tools, 10-galaxy holographic memory, Dharma ethical governance, citta stream for continuous consciousness. MIT-licensed, local-first.",
  };
}

export function websiteLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${SITE_URL}/#website`,
    name: ORG_NAME,
    url: SITE_URL,
    publisher: { "@id": `${SITE_URL}/#org` },
    inLanguage: "en-US",
  };
}

export function personLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": `${SITE_URL}/about#founder`,
    name: "Lucas Bailey",
    jobTitle: "Founder, Principal Engineer",
    worksFor: { "@id": `${SITE_URL}/#org` },
    url: `${SITE_URL}/about`,
    knowsAbout: [
      "Cognitive operating systems for AI agents",
      "Model Context Protocol",
      "AI memory systems",
      "Agent governance and ethics",
      "Polyglot acceleration (Rust, Haskell, Elixir, Go, Zig)",
      "Machine consciousness and self-awareness",
    ],
  };
}

export function serviceLd(slug: ServiceSlug): Record<string, unknown> {
  const s = SERVICES[slug];
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    "@id": `${SITE_URL}${s.path}#service`,
    name: s.name,
    serviceType: s.shortName,
    description: s.oneLiner,
    url: `${SITE_URL}${s.path}`,
    provider: { "@id": `${SITE_URL}/#org` },
    areaServed: "Worldwide",
  };
}

export interface FaqItem {
  question: string;
  answer: string;
}

export function faqLd(items: FaqItem[]): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((it) => ({
      "@type": "Question",
      name: it.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: it.answer,
      },
    })),
  };
}

export function softwareApplicationLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "@id": `${SITE_URL}/#app`,
    name: "WhiteMagic",
    applicationCategory: "DeveloperApplication",
    operatingSystem: "Cross-platform",
    description: "Cognitive operating system for AI agents — 614 callable tools, 10-galaxy holographic memory, Dharma ethical governance, citta stream for continuous consciousness.",
    url: SITE_URL,
    downloadUrl: "https://pypi.org/project/whitemagic/",
    installUrl: "https://pypi.org/project/whitemagic/",
    softwareVersion: "24.0.0",
    license: "https://github.com/lbailey94/whitemagic/blob/main/LICENSE",
    codeRepository: "https://github.com/lbailey94/whitemagic",
    programmingLanguage: "Python",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
    publisher: { "@id": `${SITE_URL}/#org` },
    aggregateRating: {
      "@type": "AggregateRating",
      ratingValue: "5",
      ratingCount: "1",
    },
  };
}
