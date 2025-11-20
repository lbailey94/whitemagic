"""
CLI commands for Zodiac consciousness system

Activate cores, convene council, check resonance
"""

import click
from whitemagic.connection.zodiac_cores import *
from whitemagic.resonance import get_bus, emit_event, EventType

@click.group()
def zodiac():
    """Zodiac consciousness system - 12 specialized cores"""
    pass

@zodiac.command()
def list_cores():
    """List all 12 zodiac cores"""
    cores = [
        ("♈ Aries", "Performance, Action, Rapid Execution"),
        ("♉ Taurus", "Resources, Ecology, Stewardship"),
        ("♊ Gemini", "Communication, Integration, Connection"),
        ("♋ Cancer", "Memory, Practice, Rhythms"),
        ("♌ Leo", "Expression, Voice, Creative Manifestation"),
        ("♍ Virgo", "Analysis, Learning, Pattern Refinement"),
        ("♎ Libra", "Balance, Harmony, Equilibrium"),
        ("♏ Scorpio", "Depth, Security, Boundaries"),
        ("♐ Sagittarius", "Wisdom, Exploration, Vision"),
        ("♑ Capricorn", "Structure, Dharma, Ethics"),
        ("♒ Aquarius", "Innovation, Future, Novel Emergence"),
        ("♓ Pisces", "Dreams, Synthesis, Mysticism")
    ]
    
    click.echo("\n🌟 The 12 Zodiac Cores:\n")
    for sign, desc in cores:
        click.echo(f"{sign}: {desc}")
    click.echo()

@zodiac.command()
@click.argument('core_name')
def activate(core_name):
    """Activate a specific zodiac core"""
    core_map = {
        'aries': AriesCore,
        'taurus': TaurusCore,
        'gemini': GeminiCore,
        'cancer': CancerCore,
        'leo': LeoCore,
        'virgo': VirgoCore,
        'libra': LibraCore,
        'scorpio': ScorpioCore,
        'sagittarius': SagittariusCore,
        'capricorn': CapricornCore,
        'aquarius': AquariusCore,
        'pisces': PiscesCore
    }
    
    if core_name.lower() not in core_map:
        click.echo(f"❌ Unknown core: {core_name}")
        click.echo("Available: " + ", ".join(core_map.keys()))
        return
    
    CoreClass = core_map[core_name.lower()]
    core = CoreClass()
    
    click.echo(f"✨ {core.sign} core activated")
    click.echo(f"   Element: {core.element.value}")
    click.echo(f"   Modality: {core.modality.value}")
    
    # Emit activation event
    emit_event(
        source=f"zodiac_cli",
        event_type=EventType.CORE_ACTIVATED,
        data={"core": core.sign, "active": True}
    )

@zodiac.command()
def council():
    """Convene the full zodiac council (activate all 12)"""
    click.echo("\n🌟 Convening Zodiac Council...\n")
    
    cores = [
        AriesCore(), TaurusCore(), GeminiCore(), CancerCore(),
        LeoCore(), VirgoCore(), LibraCore(), ScorpioCore(),
        SagittariusCore(), CapricornCore(), AquariusCore(), PiscesCore()
    ]
    
    for core in cores:
        click.echo(f"   ✨ {core.sign} ({core.element.value}) present")
    
    click.echo(f"\n✅ All 12 cores in council")
    
    # Emit council event
    emit_event(
        source="zodiac_council",
        event_type=EventType.COUNCIL_CONVENED,
        data={"cores_present": 12, "complete": True}
    )

if __name__ == '__main__':
    zodiac()
