/**
 * schema.org JSON-LD builders.
 *
 * Emitted via a tiny <JsonLd> component (see components/JsonLd.tsx).
 * Each builder returns a plain object; callers wrap it in the component.
 */
import { SERVICES, type ServiceSlug } from "./data/services";

const SITE_URL = "https://whitemagic.dev";
const ORG_NAME = "WhiteMagic Labs";
const ORG_LEGAL = "WhiteMagic Labs";

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
      "Private AI deployment, agent governance, and MCP engineering for regulated enterprises.",
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
    name: "WhiteMagic Labs Founder",
    jobTitle: "Founder, Principal Engineer",
    worksFor: { "@id": `${SITE_URL}/#org` },
    url: `${SITE_URL}/about`,
    knowsAbout: [
      "Agent governance",
      "Model Context Protocol",
      "Private AI deployment",
      "OWASP LLM Top 10 (v1.1, covers agentic AI)",
      "EU AI Act",
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
