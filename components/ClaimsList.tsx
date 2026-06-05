import { ClaimCard } from "@/components/ClaimCard";
import { PRESCIENCE_CLAIMS } from "@/lib/data/prescience";
export function ClaimsList(){return(<section className="container-site py-16"><div className="mx-auto max-w-3xl space-y-8">{PRESCIENCE_CLAIMS.map(c=><ClaimCard key={c.claim} claim={c}/>)}</div></section>);}
