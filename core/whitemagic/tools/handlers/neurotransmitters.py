"""Neurotransmitter Vector tool handlers."""
from typing import Any


def handle_neurotransmitter_status(**kwargs: Any) -> dict[str, Any]:
    """Get the current neurotransmitter vector snapshot."""
    from whitemagic.core.monitoring.neurotransmitter_vector import get_neurotransmitter_vector

    nt = get_neurotransmitter_vector()
    snap = nt.snapshot()
    return {"status": "success", **snap.to_dict()}


def handle_neurotransmitter_report(**kwargs: Any) -> dict[str, Any]:
    """Get a detailed neurotransmitter report with history and trends."""
    from whitemagic.core.monitoring.neurotransmitter_vector import get_neurotransmitter_vector

    nt = get_neurotransmitter_vector()
    snap = nt.snapshot()

    # Build biochemical metaphor report
    report = {
        "status": "success",
        "profile": snap.to_dict(),
        "biochemical_state": _classify_state(snap),
        "recommendations": _generate_recommendations(snap),
    }
    return report


def _classify_state(snap: Any) -> str:
    """Classify the overall biochemical state."""
    if snap.cortisol > 0.7:
        return "stressed"
    if snap.glutamate > 0.7 and snap.dopamine > 0.6:
        return "creatively_excited"
    if snap.serotonin > 0.7 and snap.gaba > 0.6:
        return "calm_and_stable"
    if snap.oxytocin > 0.7:
        return "socially_bonded"
    if snap.acetylcholine > 0.7:
        return "highly_focused"
    if snap.dopamine < 0.3:
        return "anhedonic"
    return "baseline"


def _generate_recommendations(snap: Any) -> list[str]:
    """Generate actionable recommendations based on neurotransmitter state."""
    recs = []
    if snap.cortisol > 0.7:
        recs.append("Reduce load: errors or throttling detected. Consider lighter tool usage.")
    if snap.serotonin < 0.3:
        recs.append("Stabilize: high error variance. Review recent tool failures.")
    if snap.dopamine < 0.3:
        recs.append("Motivate: success rate below expectation. Check for systemic issues.")
    if snap.glutamate > 0.8:
        recs.append("Capture creativity: many novel connections detected. Record insights.")
    if snap.oxytocin < 0.3:
        recs.append("Connect: low multi-agent activity. Consider swarm or mesh tasks.")
    if snap.acetylcholine < 0.3:
        recs.append("Focus: attention is diffuse. Use salience spotlight to identify priorities.")
    if not recs:
        recs.append("System is balanced. No specific action needed.")
    return recs
