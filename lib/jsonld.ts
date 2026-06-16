/**
 * schema.org JSON-LD builders.
 *
 * Emitted via a tiny <JsonLd> component (see components/JsonLd.tsx).
 * Each builder returns a plain object; callers wrap it in the component.
 */
import { PRICING_TIERS_LIST } from "./data/pricing";
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
    offers: {
      "@type": "Offer",
      price: s.startingPrice.replace(/[^0-9]/g, ""),
      priceCurrency: "USD",
      priceSpecification: {
        "@type": "PriceSpecification",
        price: s.startingPrice.replace(/[^0-9]/g, ""),
        priceCurrency: "USD",
        valueAddedTaxIncluded: false,
      },
    },
  };
}

export function pricingProductsLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "@id": `${SITE_URL}/pricing#tiers`,
    name: "WhiteMagic Labs engagement tiers",
    itemListElement: PRICING_TIERS_LIST.map((tier, i) => ({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "Service",
        name: tier.name,
        description: tier.oneLiner,
        url: `${SITE_URL}/pricing#${tier.slug}`,
        offers: {
          "@type": "Offer",
          price: tier.price.replace(/[^0-9]/g, ""),
          priceCurrency: "USD",
        },
      },
    })),
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

/** FAQ items mirrored from /pricing page copy. Keep in sync with the page. */
export const PRICING_FAQ: FaqItem[] = [
  {
    question: "Why are the lower tiers so accessible?",
    answer:
      "Because the best CTO engagements start with someone inside the company doing their own diligence first. A $1,000 session beats a $50K mistake. If you later bring me in for a real engagement, the Office Hours fee gets credited to the scope.",
  },
  {
    question: "Do you take equity or deferred payment?",
    answer:
      "No. Cash-only, invoiced up front for Office Hours and Architecture Reviews. Engagements are 50% on kickoff, 50% on delivery. Keeps the incentive structure clean — I win when you ship, not when you raise.",
  },
  {
    question: "What's your NDA posture?",
    answer:
      "I'll sign yours if it's reasonable. My own default is a mutual NDA covering code, data, and architecture you share with me. I never publish client work without explicit written consent.",
  },
  {
    question: "Do you work with non-US clients?",
    answer:
      "Yes. Stripe invoices in USD; I can accommodate time zones for live sessions with 48h notice. Engagements have been done fully async.",
  },
  {
    question: "What if I need something in between these tiers?",
    answer:
      "Email me. The three tiers cover roughly 80% of inbound; the other 20% gets a custom quote. There's no penalty for asking.",
  },
];
