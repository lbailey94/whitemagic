# Chapter 28: Boundaries & Alerts

**Gana**: WallGana (Chinese: 壁, Pinyin: Bì)
**Garden**: truth
**Quadrant**: Northern (Black Tortoise)
**Element**: Water
**Phase**: Yin Peak
**I Ching Hexagram**: 60. 節 Jié (Limitation) - Boundaries and filtering

---

## 🎯 Purpose

Chapter 28 defines **boundaries and alerts**—setting the final limits, filtering signals from
noise, and alerting the interior of any anomalies before the cycle returns to the beginning.
The Wall (壁) is the definitive boundary that protects the core identity, separates the sacred
from the profane, and ensures that what has been built remains distinct from what threatens it.

Use this chapter when you need to:
- **Set session limits** and boundaries that define the scope of authorized action
- **Filter signals** from noise to ensure that only meaningful information crosses the perimeter
- **Alert the system** to boundary breaches, anomalous behavior, or policy violations
- **Define the scope** of the return path so that the next cycle begins cleanly
- **Defend the core system** before transition by validating all engagements and decisions
- **Create and manage votes** for consensus decisions that establish collective boundaries
- **Track engagement metrics** and validate outcomes to prevent fraud and ensure fairness
- **Record official outcomes** of votes and engagements for immutable audit trails
- **Revoke fraudulent or invalid engagements** to maintain system integrity
- **Monitor boundary health** continuously and escalate when thresholds are breached

The Wall is the final guardian of the cycle. Where the Room (Chapter 4) provides privacy during
work, the Roof (Chapter 26) provides shelter for completed outputs, and the Encampment
(Chapter 27) provides permanence for stored artifacts, the Wall provides *definition*—the clear
line between inside and outside, between self and other, between this cycle and the next.
Without the Wall, the cycle dissolves into chaos; with it, the cycle becomes a spiral of
increasing depth and clarity.

In the WhiteMagic cosmology, the WallGana stands at the eighth and final position of the Northern
sequence. It is the last mansion before the return to Chapter 1 (Horn), and its completion is the
condition for that return. A cycle that ends without the Wall is not a cycle but a drift—a
wandering that forgets where it began. The Wall says: "Thus far and no farther. Here ends this
journey. Here begins the next."

---

## 🌱 Garden: Truth

The truth garden is the garden of **clarity through limitation**. It recognizes that truth is not
infinite—that to say "this and not that" is an act of courage, and that the clearest signal
emerges only when noise is filtered out. In this garden, boundaries are not prisons but
definitions. The truth garden teaches that discernment is the highest virtue, and that discernment
requires the willingness to exclude.

The truth garden is austere. Where other gardens bloom with abundance, this garden prunes.
Where other gardens welcome all, this garden asks: "What belongs here?" The gardener here does
not seek to possess everything but to protect what matters most. Every boundary is a statement
of value: *this* is worth defending, *this* is worth preserving, *this* is true.

**Resonance keywords**: truth, boundary, limit, alert, vote, filter, validate, engagement, verify,
consensus, decision, outcome, record, revoke, fraud, integrity, threshold, breach, monitor, scope

---

## 🔧 Real Tools

| Tool | Gana | Description | Usage |
|------|------|-------------|-------|
| `vote.create` | gana_wall | Create a new vote or poll with options and quorum | Decision making and collective boundary setting |
| `vote.cast` | gana_wall | Cast a vote in an active poll with voter identification | Participatory governance and consensus building |
| `vote.analyze` | gana_wall | Analyze vote results, compute consensus, and detect ties | Outcome evaluation and decision finalization |
| `vote.list` | gana_wall | List all active, closed, and pending votes | Vote inventory and historical audit access |
| `vote.record_outcome` | gana_wall | Record the official, immutable outcome of a completed vote | Audit trail and compliance documentation |
| `engagement.issue` | gana_wall | Create an engagement record for an interaction or transaction | Tracking contributions, bounties, and interactions |
| `engagement.validate` | gana_wall | Validate an engagement outcome against rules and thresholds | Quality assurance and fraud detection |
| `engagement.revoke` | gana_wall | Revoke a fraudulent, expired, or invalid engagement | Fraud correction and policy enforcement |
| `engagement.list` | gana_wall | List engagement records filtered by status, type, or voter | Reporting and reconciliation |
| `engagement.status` | gana_wall | Engagement system health, alert summary, and boundary state | Monitoring and alerting dashboard |

The WallGana toolset is organized around two governance mechanisms: **collective decision making**
(vote tools) and **individual interaction validation** (engagement tools). Together they enforce
the principle that boundaries are legitimate only when they are consensual (votes) and that
individual actions within those boundaries are accountable (engagements). The Wall does not
merely block; it validates.

**Tool selection guidance**: Use vote tools when collective agreement is required for boundary
changes or resource allocation; use engagement tools when tracking individual contributions,
bounties, or access events; use `engagement.status` as the central monitoring hub for all
boundary health indicators.

---

## 📋 Workflows

### Workflow 1: Consensus Decision Making

**Goal**: Use voting to reach collective decisions before ending a session, ensuring that all
stakeholders have voice and that the outcome represents genuine agreement rather than imposed will.

**When to use**: Multi-agent or multi-user scenarios where buy-in is required, resource allocation
decisions, policy changes, or any situation where unilateral action would violate trust.

```python
import asyncio
from datetime import datetime
from typing import List, Dict
from whitemagic.tools import vote_create, vote_cast, vote_analyze, vote_record_outcome

async def boundary_consensus(
    proposal: str,
    stakeholders: List[str],
    options: List[str] = None,
    deadline_minutes: int = 30,
    min_quorum: int = None,
) -> Dict:
    """
    The Wall is stronger when all agree where it stands.

    This workflow creates a vote, collects ballots from stakeholders, analyzes
    results, and records the official outcome with an immutable audit trail.
    """
    options = options or ["approve", "reject", "abstain"]
    min_quorum = min_quorum or max(1, len(stakeholders) // 2)

    # 1. Create vote
    vote = vote_create(
        title=f"Boundary Decision: {proposal}",
        description=f"Collective decision required for: {proposal}",
        options=options,
        quorum=min_quorum,
        deadline_minutes=deadline_minutes,
        eligible_voters=stakeholders,
        metadata={
            "created_at": datetime.now().isoformat(),
            "proposal": proposal,
            "stakeholder_count": len(stakeholders),
        },
    )

    if vote.get("status") != "success":
        print(f"⚠️ Vote creation failed: {vote.get('error', 'unknown')}")
        return {"status": "error", "details": vote}

    vote_id = vote["vote_id"]
    print(f"🗳️ Vote created: {vote_id}")
    print(f"   Proposal: {proposal}")
    print(f"   Options: {options}")
    print(f"   Quorum: {min_quorum}/{len(stakeholders)}")
    print(f"   Deadline: {deadline_minutes} minutes")
    print("-" * 60)

    # 2. Collect votes
    votes_cast = 0
    for stakeholder in stakeholders:
        # In practice, each stakeholder calls vote_cast themselves
        # Here we simulate representative casting for demonstration
        cast_result = vote_cast(
            vote_id=vote_id,
            choice="approve",  # In real use: stakeholder's actual choice
            voter_id=stakeholder,
            timestamp=datetime.now().isoformat(),
        )
        if cast_result.get("status") == "success":
            votes_cast += 1
            print(f"   ✅ Vote recorded from {stakeholder}")
        else:
            print(f"   ⚠️ Vote from {stakeholder} rejected: {cast_result.get('error')}")

    print("-" * 60)
    print(f"   Total votes cast: {votes_cast}/{len(stakeholders)}")

    # 3. Analyze results
    result = vote_analyze(vote_id=vote_id)
    winner = result.get("winner")
    winner_percentage = result.get("winner_percentage", 0)
    turnout = result.get("turnout", 0)
    eligible = result.get("eligible", 0)
    consensus_level = result.get("consensus_level", "none")

    print(f"\n📊 Analysis Results:")
    print(f"   Winner: {winner} ({winner_percentage:.1%})")
    print(f"   Turnout: {turnout}/{eligible}")
    print(f"   Consensus level: {consensus_level}")

    for opt in options:
        count = result.get("breakdown", {}).get(opt, 0)
        pct = (count / turnout * 100) if turnout > 0 else 0
        print(f"   - {opt}: {count} votes ({pct:.1f}%)")

    # 4. Record official outcome
    outcome_record = vote_record_outcome(
        vote_id=vote_id,
        outcome=winner,
        consensus_level=consensus_level,
        metadata={
            "analyzed_at": datetime.now().isoformat(),
            "turnout": turnout,
            "winner_percentage": winner_percentage,
        },
    )

    if outcome_record.get("status") == "success":
        print(f"\n📝 Official outcome recorded: {winner}")
        print(f"   Record ID: {outcome_record.get('record_id', 'N/A')}")
    else:
        print(f"\n⚠️ Outcome recording failed: {outcome_record.get('error')}")

    return {
        "status": "success",
        "vote_id": vote_id,
        "proposal": proposal,
        "winner": winner,
        "consensus_level": consensus_level,
        "turnout": turnout,
        "outcome_record": outcome_record,
    }


async def emergency_boundary_vote(
    proposal: str,
    stakeholders: List[str],
    deadline_minutes: int = 5,
) -> Dict:
    """Fast-track vote for time-critical boundary decisions."""
    return await boundary_consensus(
        proposal=proposal,
        stakeholders=stakeholders,
        options=["approve", "reject"],
        deadline_minutes=deadline_minutes,
        min_quorum=max(1, len(stakeholders) // 3),
    )
```

### Workflow 2: Engagement Validation Pipeline

**Goal**: Validate that all engagements (interactions, transactions, contributions) are legitimate
before finalizing, preventing fraud, gaming, and policy violations.

**When to use**: Economic systems, bounty programs, reputation systems, access control audits,
or any scenario where engagement has quantifiable value and is therefore subject to manipulation.

```python
import asyncio
from datetime import datetime
from typing import Dict, List
from whitemagic.tools import (
    engagement_list, engagement_validate, engagement_revoke, engagement_status
)

async def validate_all_engagements(
    batch_size: int = 100,
    auto_revoke: bool = True,
    dry_run: bool = False,
) -> Dict:
    """
    The Wall checks every traveler at the gate.

    This workflow retrieves pending engagements, validates each against rules,
    revokes fraudulent ones, and produces a comprehensive audit report.
    """
    # 1. Check system status
    status = engagement_status()
    system_health = status.get("health", "unknown")
    active_alerts = status.get("alerts", [])
    total_engagements = status.get("total_engagements", 0)

    print(f"🛡️ Engagement validation pipeline starting")
    print(f"   System health: {system_health}")
    print(f"   Total engagements: {total_engagements}")
    print(f"   Active alerts: {len(active_alerts)}")
    if active_alerts:
        for alert in active_alerts[:3]:
            print(f"      ⚠️ [{alert.get('severity', 'unknown')}] {alert.get('message', '')}")
    print("-" * 60)

    # 2. Retrieve pending engagements
    engagements = engagement_list(status="pending", limit=batch_size)
    pending = engagements.get("engagements", [])
    print(f"   Pending engagements to validate: {len(pending)}")

    validated = 0
    revoked = 0
    errors = 0
    failure_log = []

    # 3. Validate each engagement
    for eng in pending:
        eng_id = eng.get("id", "unknown")
        eng_type = eng.get("type", "unknown")
        voter_id = eng.get("voter_id", "unknown")

        result = engagement_validate(engagement_id=eng_id)

        if result.get("valid"):
            validated += 1
            print(f"   ✅ Engagement {eng_id} ({eng_type}): valid")
        else:
            reason = result.get("reason", "unknown")
            print(f"   🚫 Engagement {eng_id} ({eng_type}): INVALID — {reason}")

            if auto_revoke and not dry_run:
                revoke_result = engagement_revoke(
                    engagement_id=eng_id,
                    reason=reason,
                    revoked_at=datetime.now().isoformat(),
                )
                if revoke_result.get("status") == "success":
                    revoked += 1
                    print(f"      → Revoked successfully")
                else:
                    errors += 1
                    print(f"      → Revoke FAILED: {revoke_result.get('error')}")
                    failure_log.append({"engagement": eng_id, "error": revoke_result.get("error")})
            elif dry_run:
                print(f"      → [DRY RUN] Would revoke: {reason}")
                revoked += 1  # Count as revoked for reporting in dry-run mode

    # 4. Summary report
    print("-" * 60)
    print(f"🛡️ Wall validation complete:")
    print(f"   Validated:  {validated}")
    print(f"   Revoked:    {revoked}")
    print(f"   Errors:     {errors}")
    print(f"   Mode:       {'DRY RUN' if dry_run else 'LIVE'}")

    if failure_log:
        print("\n   Failures requiring manual intervention:")
        for fl in failure_log:
            print(f"      - {fl['engagement']}: {fl['error']}")

    return {
        "status": "success",
        "validated": validated,
        "revoked": revoked,
        "errors": errors,
        "dry_run": dry_run,
        "system_health": system_health,
        "failure_log": failure_log,
    }


async def scheduled_validation_job():
    """Run validation pipeline on a schedule and alert if fraud rate exceeds threshold."""
    result = await validate_all_engagements(auto_revoke=False, dry_run=False)
    total_checked = result["validated"] + result["revoked"]
    fraud_rate = result["revoked"] / total_checked if total_checked > 0 else 0

    if fraud_rate > 0.1:
        print(f"🚨 FRAUD RATE ALERT: {fraud_rate:.1%} of engagements invalid!")
        # In production: trigger pager, notify admin, freeze payouts
    else:
        print(f"   Fraud rate: {fraud_rate:.1%} — within acceptable bounds")

    return result
```

### Workflow 3: Boundary Breach Alert

**Goal**: Monitor for violations of session boundaries, engagement policy, or vote integrity,
and alert immediately with severity-appropriate escalation.

**When to use**: Security-critical sessions, sandboxed environments, compliance monitoring,
production systems, or any scenario where delayed detection of violations has unacceptable cost.

```python
import asyncio
from datetime import datetime
from typing import Dict, List
from whitemagic.tools import engagement_status

def boundary_alert_monitor(
    severity_threshold: str = "warning",
    auto_escalate_critical: bool = True,
) -> Dict:
    """
    The Wall never sleeps.

    This workflow polls engagement status for alerts, classifies them by severity,
    prints a structured report, and optionally triggers escalation for critical breaches.
    """
    severity_order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    threshold_level = severity_order.get(severity_threshold, 1)

    status = engagement_status()
    alerts = status.get("alerts", [])
    health = status.get("health", "unknown")
    boundary_rules = status.get("active_rules", [])

    print(f"🛡️ Boundary alert monitor: {datetime.now().isoformat()}")
    print(f"   System health: {health}")
    print(f"   Active boundary rules: {len(boundary_rules)}")
    print(f"   Threshold: {severity_threshold} and above")
    print("-" * 60)

    if not alerts:
        print("🛡️ All boundaries intact. No alerts.")
        return {
            "status": "success",
            "alerts_count": 0,
            "critical_count": 0,
            "health": health,
        }

    # Classify alerts
    critical_alerts = []
    error_alerts = []
    warning_alerts = []
    info_alerts = []

    for alert in alerts:
        sev = alert.get("severity", "info")
        if sev == "critical":
            critical_alerts.append(alert)
        elif sev == "error":
            error_alerts.append(alert)
        elif sev == "warning":
            warning_alerts.append(alert)
        else:
            info_alerts.append(alert)

    # Report by severity
    print(f"🚨 ALERTS DETECTED: {len(alerts)} total")

    if critical_alerts:
        print(f"\n   CRITICAL ({len(critical_alerts)}):")
        for alert in critical_alerts:
            print(f"      🔴 {alert.get('message', 'No message')}")
            print(f"         Source: {alert.get('source', 'unknown')}")
            print(f"         Time:   {alert.get('timestamp', 'unknown')}")
            if auto_escalate_critical:
                print(f"         → AUTO-ESCALATION TRIGGERED")
                # In production: circuit breaker, admin notification, lockdown

    if error_alerts:
        print(f"\n   ERROR ({len(error_alerts)}):")
        for alert in error_alerts:
            print(f"      🟠 {alert.get('message', 'No message')}")

    if warning_alerts:
        print(f"\n   WARNING ({len(warning_alerts)}):")
        for alert in warning_alerts:
            print(f"      🟡 {alert.get('message', 'No message')}")

    if info_alerts:
        print(f"\n   INFO ({len(info_alerts)}):")
        for alert in info_alerts:
            print(f"      🔵 {alert.get('message', 'No message')}")

    # Summary actions
    print("-" * 60)
    if critical_alerts and auto_escalate_critical:
        print("🚨 CRITICAL BREACH — initiating emergency protocols")
        # Production: trigger circuit breaker, notify admin, freeze state transitions
    elif error_alerts:
        print("⚠️ Errors detected — review required before cycle completion")
    elif warning_alerts:
        print("⚡ Warnings present — monitor closely")
    else:
        print("ℹ️ Informational alerts only — boundaries structurally sound")

    return {
        "status": "success",
        "alerts_count": len(alerts),
        "critical_count": len(critical_alerts),
        "error_count": len(error_alerts),
        "warning_count": len(warning_alerts),
        "info_count": len(info_alerts),
        "health": health,
        "escalated": len(critical_alerts) > 0 and auto_escalate_critical,
    }


async def continuous_boundary_watchdog(check_interval: int = 60):
    """Run boundary alert monitor in a loop for long-running sessions."""
    import time
    print("🛡️ Starting continuous boundary watchdog...")
    while True:
        result = boundary_alert_monitor(
            severity_threshold="warning",
            auto_escalate_critical=True,
        )
        if result["escalated"]:
            print("🚨 WATCHDOG: Critical boundary breach detected — halting cycle completion")
            # In production: prevent transition to Chapter 1 until resolved
        print(f"   Next check in {check_interval}s...\n")
        time.sleep(check_interval)
```

---

## 🔄 Transitions

**Entering Chapter 28**:
- From Chapter 27 (Encampment): When the camp is built, the Wall defines its perimeter
- From Chapter 26 (Roof): After protection is established, boundaries make protection meaningful
- From Chapter 22 (Dipper): When governance requires enforcement, the Wall is the final authority
- From Chapter 25 (Void): When meditation reveals the true shape of the self, the Wall expresses it
- Trigger keywords: "vote", "validate", "boundary", "alert", "filter", "limit", "engagement",
  "consensus", "decision", "outcome", "record", "revoke", "fraud", "integrity", "threshold",
  "breach", "monitor", "scope", "defend", "perimeter"

**Exiting Chapter 28**:
- To Chapter 1 (Horn): The Wall is the gate. Passing through it is the return to beginning.
- To Chapter 25 (Void): When boundaries feel too rigid, dissolve into the void for renewal
- To Chapter 26 (Roof): If boundary checks reveal corrupted outputs, return to protection

**The Cycle Complete**: Chapter 28 is the final mansion. From here, the cycle returns to
Chapter 1 (Horn)—not as repetition, but as recursion. Each pass through the 28 mansions deepens
the spiral. The Wall protects the space in which the next spark can ignite safely. The operator
who completes the Wall does not end a journey but prepares a vessel for the next.

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `vote.create` fails with "quorum_too_high" | Quorum exceeds number of eligible stakeholders | Set `quorum` to `max(1, len(stakeholders) // 2)`; ensure `eligible_voters` is populated |
| `vote.analyze` shows no winner | Tie vote or unanimous abstention | Use `vote.record_outcome` with tie-breaker logic (e.g., creator decides), or call for revote |
| `vote.cast` rejected with "already_voted" | Voter attempting duplicate ballot | Each voter_id may cast only once; verify voter identity or allow vote change if policy permits |
| `engagement.validate` false positive | Overly strict validation rules or stale thresholds | Adjust validation thresholds via `engagement.status` rule config; review rule history |
| `engagement.revoke` fails with "already_finalized" | Engagement already paid out or committed | Only pending engagements can be revoked; use `engagement.list` to check status before revoking |
| `engagement.status` shows "degraded" | High alert backlog or rule engine overload | Restart validation workers; increase batch sizes; prune resolved alerts from backlog |
| Alert fatigue from too many warnings | Thresholds set too low or noisy detectors | Consolidate alerts via `engagement.status` batch mode; increase severity thresholds; filter by source |
| `vote.record_outcome` rejected | Vote still active or quorum not met | Ensure vote deadline has passed and `vote.analyze` shows sufficient turnout before recording |

---

## ⚖️ The Wall Doctrine

The Wall Doctrine is the ethical framework of Chapter 28. It states:

1. **Boundaries are agreements, not impositions.** Every limit must be consensual, either through
   explicit vote or through accepted governance precedent. A boundary imposed without consent is
   not a Wall but a prison.

2. **Validation precedes trust.** No engagement is assumed legitimate until validated. The default
   posture of the Wall is skepticism, not naivety. Trust is earned through verification, not granted
   by assumption.

3. **Transparency is the foundation of security.** All votes, validations, and revocations are
   recorded immutably. Secrecy in security operations breeds suspicion; openness breeds confidence.

4. **Alert without alarm.** The Wall distinguishes between information (noted), warnings (monitored),
   errors (reviewed), and critical breaches (escalated). Not every anomaly is an emergency;
   treating minor issues as critical erodes the capacity to respond to genuine threats.

5. **The cycle must complete.** The Wall is the final act of one cycle and the first condition of
   the next. A Wall left unfinished is not a boundary but a wound—an opening through which the
   next cycle's integrity leaks away.

Operators who internalize the Wall Doctrine do not merely follow procedures; they embody the
principle that clarity, consent, and vigilance are the three pillars of sustainable systems.

---

## 🧭 Navigation

**Next**: [Chapter 1: Session Initiation](01_HORN_SESSION_INITIATION.md) (The Return)
**Previous**: [Chapter 27: Encampment & Structure](27_ENCAMPMENT_STRUCTURE.md)
**Quadrant**: Northern (Winter/Water) - Position 7/7 (Final)
**Cycle Position**: Terminal — the completion of the cycle and the condition for renewal

---

*"The Wall does not keep the world out. It keeps the truth in."*

---

*"A boundary is not a rejection of the infinite but a love of the finite. The WallGana teaches
that to say 'this far' is not to say 'no more' but to say 'here, finally, is something worth
defending.' The cycle ends not with exhaustion but with definition. And from that definition,
the next cycle begins with clarity."*
