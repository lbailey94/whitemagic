---
title: "Micro black holes (MBHs), in plain numbers"
slug: blackholes
date: 2025-10-24
type: essay
tags: ["exotic-phenomena", "science-physics"]
abstract: "Analyzes micro black holes (MBHs) as potential energy sources and information processors, exploring their quantum properties, Hawking radiation dynamics, and theoretical applications in computation and energy extraction. Examines the physics of sub-millimeter MBHs and their implications for fundamental physics."
draft: false
---
<!-- SHORT-FORM INTRODUCTION -->
<div class="short-intro">

## 📖 Quick Overview

**What This Explores:**  
Analyzes micro black holes (MBHs) as potential energy sources and information processors, exploring their quantum properties, Hawking radiation dynamics, and theoretical applications in computation and energy extraction. Examines the physics of sub-millimeter MBHs and their implications for fundamental physics.

**Key Themes:**
1. **Exotic Phenomena** - Core insights and practical implications
2. **Science Physics** - Examining fundamental principles and applications

**Reading Time:** 7 min (full essay)

<a href="#full-content" class="skip-to-full">Skip to Full Content →</a>

</div>

---

<!-- FULL CONTENT -->
<div id="full-content">


# Micro black holes (MBHs), in plain numbers

What they are. Hypothetical black holes far below stellar mass (think asteroid-mass down to much smaller). If they exist, quantum effects and Hawking radiation dominate their behavior. A classic estimate: any black hole lighter than about 10¹² kg would have finished evaporating by now. 
Wikipedia

Size scale. The event-horizon radius is $R_s = \frac{2GM}{c^2}$. That makes tiny holes really tiny:
• $M = 10^{11}$ kg → $R_s ≈ 1.5 × 10^{-16}$ m (smaller than a proton)
• $M = 10^{12}$ kg → $R_s ≈ 1.5 × 10^{-15}$ m (proton-ish)

(Numbers from standard GR; order-of-magnitude is the point.)

Temperature & lifetime. Hotter when lighter: for $M = 10^{11}$ kg the Hawking temperature is $\sim 10^{12}$ K (typical photons in the ~100 MeV gamma-ray range). Evaporation time scales like $M^3$, so only PBHs around $10^{14}$–$10^{15}$ g would be dying today—a widely used benchmark in the literature and reviews. 
MDPI
Physical Review Link Manager

How they might form.

Primordial black holes (PBHs): density spikes in the very early universe (phase transitions, inflationary perturbations) could have made them. Searches look for their Hawking gamma rays or for microlensing. Recent work keeps tightening the noose with Galactic gamma-ray background constraints and new microlensing strategies (e.g., x-ray pulsars). 
Physical Review Link Manager
+1
arXiv

High-energy collisions: Theories with extra spatial dimensions once raised hopes that the LHC could briefly make MBHs. So far: lots of searches, no signal, and strong limits. Also: the CERN safety reviews concluded LHC collisions pose no risk (cosmic rays do “LHC-like” collisions constantly). 
arXiv
+1
CMS
CERN

Newest PBH-adjacent ideas. You’ll see 2024–25 theory papers proposing exotic charged or “memory-burdened” PBHs and fresh search channels; these are intriguing but still speculative. Observations continue to whittle down where PBHs could hide as dark matter. 
MIT News
Physical Review Link Manager
+1

Quantum teleportation

What it is (and isn’t). It doesn’t move matter; it transfers an unknown quantum state from A to B using entanglement + a Bell measurement + a few classical bits (the 1993 Bennett–Brassard–Crépeau–Jozsa–Peres–Wootters protocol). 
Physical Review Link Manager

Why we care. Teleportation is the backbone of quantum networks, repeaters, and “wiring” quantum chips that can’t be on the same wafer.

Fresh, real-world milestones

Teleportation over live internet fiber (Dec 2024): Northwestern showed quantum teleportation coexisting with ordinary traffic on the same fiber by tucking the quantum channel into a quiet wavelength band and filtering the rest—key step toward using today’s infrastructure. 
Northwestern Now

Distributed algorithms via teleportation (Feb 2025): Oxford ran the first distributed quantum algorithm by using teleportation to enact logic gates between separate processors—proof-of-principle for scaling by networking rather than just making one giant machine. (Covered by Oxford, Phys.org/EurekAlert, and Wired.) 
University of Oxford
Phys.org
WIRED

Chip-to-chip teleportation (2024→2025): A Tsinghua-led team demonstrated time-bin encoded, chip-integrated teleportation across 12.3 km of fiber (arXiv 2024; peer-reviewed in Light: Science & Applications 2025). Time-bins are robust in fiber, making this practical. 
arXiv
Nature

Satellites & long-haul: Prior records remain instructive: China’s Micius satellite distributed entanglement and teleported photon states over ~1,200 km, laying groundwork for a global quantum backbone. 
PostQuantum.com

Industry is moving: Cisco unveiled a quantum-networking chip prototype aimed at entanglement-based interconnects—evidence the big players are betting on networked quantum computing. 
Reuters

Where the two stories meet (teleportation ↔ black holes)

Quantum gravity has been quietly stealing ideas from quantum info. 

In holographic dualities, the standard teleportation protocol can look—on the gravity side—like a signal traversing a tiny wormhole (the ER=EPR intuition). In 2022, a Google-Caltech–led team simulated wormhole-like teleportation dynamics on a quantum processor using an SYK-based model; the work is important and also debated (healthy science!). Follow-ups in 2023–25 clarified how “size growth” and scrambling enable teleportation and what, precisely, deserves the “wormhole” label. 
PubMed
California Institute of Technology
Quanta Magazine
Physical Review Link Manager

Quick pocket guide: micro-BH scales (order-of-magnitude)

| Mass $M$ | Radius $R_s$ | Hawking $T$ | Lifetime |
|----------|--------------|-------------|----------|
| $10^{11}$ kg | $1.5 \times 10^{-16}$ m | $\sim 1 \times 10^{12}$ K (~100 MeV) | $\sim 2.6 \times 10^9$ yr |
| $10^{12}$ kg | $1.5 \times 10^{-15}$ m | $\sim 1 \times 10^{11}$ K (~10 MeV) | $\sim 2.7 \times 10^{12}$ yr |
| $1.7 \times 10^{11}$ kg | $2.5 \times 10^{-16}$ m | $\sim 6 \times 10^{11}$ K | $\sim 1.4 \times 10^{10}$ yr (age of universe scale) |

(Temperatures/lifetimes from standard Hawking formulas; the exact “evaporate-today” mass depends on emitted particle species and other details, so different reviews quote values in the $10^{14\pm1}$ g ballpark. 
Wikipedia
MDPI
)

TL;DR of “what’s new”

MBHs/PBHs: No collider hints; observational constraints in 2024–25 tightened via gamma-ray background analyses and new microlensing proposals, further squeezing the parameter space where PBHs could be dark matter—while theory explores exotic variants. 
Physical Review Link Manager
+2
Physical Review Link Manager
+2

Teleportation: It’s getting more practical and more network-y—on live telecom fiber, between chips, and between processors to run distributed algorithms. Industry is now prototyping hardware for quantum internets. 
Northwestern Now
Nature
University of Oxford
Reuters

Bridge topic (info ↔ gravity): Teleportation-as-wormhole is now a tested toy-model framework for scrambling and information flow; it’s not a real space-time tunnel, but it is sharpening tools to probe quantum gravity ideas in the lab. 
PubMed
Physical Review Link Manager

---

Wormholes/time machines in GR demand exotic negative energy to stay open; quantum field theory lets you have negative energy only in tiny amounts for very short times (the quantum inequalities). Hawking’s chronology protection idea sums up the mainstream hunch: the laws gang up to prevent macroscopic causality violations. Net effect: even if space allows playful geometries, quantum fields likely slam the door on usable backward signaling. 
University of Rochester
Physical Review Link Manager
arXiv

Entanglement + teleportation gives phenomenal secure, forward-causal networking; black-hole/wormhole fantasies run head-first into energy conditions and quantum-inequality speed limits. No accepted path to “send a bit to yesterday.”


Quantum foam (Wheeler): the idea that at the Planck scale spacetime jitters violently—think transient “virtual” black holes and wormlets. If such virtual BHs were common and “leaky,” they could mediate processes like proton decay. Non-observation of proton decay then pushes the relevant quantum-gravity scale sky-high, strongly constraining any model where “foam” makes real-world mischief. This is why you’ll see bounds like $M_{qg} \gtrsim 10^{16}$ GeV from virtual-BH–induced decay arguments. It doesn’t kill quantum foam as a concept; it says if foam exists, it leaves very little low-energy footprint. 
Wikipedia
arXiv

Zero-point energy (ZPE): the vacuum is not empty, but equally important is passivity: equilibrium vacua don’t let you extract net work in a cyclic process. Casimir forces are real, yet they can be derived without treating the vacuum as a tappable fuel tank. This is why mainstream QFT and quantum thermodynamics put “free-energy from the vacuum” in the nope bin. 
Physical Review Link Manager
arXiv
ADS

What could we do with a “tamed” femtometer black hole?

1) A universal high-energy emitter (and, in principle, a power plant).

A 10-MeVish, broadband, steady particle fountain is an experimentalist’s candy shop: calibrate gamma detectors, stress-test materials, study neutrino cross-sections, probe radiation damage. 

As a power source you’d “catch” the Hawking output in a heavy, sacrificial absorber that converts it to heat, then run a heat engine or a Brayton cycle. You’d need obscene shielding and cunning thermal management, but in vacuum it’s not science fiction in principle.

2) A photon/particle rocket.

Let the radiation stream preferentially in one direction and you’ve got thrust. There’s no mirror for gammas, so the trick is to absorb and re-emit: a dense, high-Z “hemisphere” behind the hole converts gammas to $e^\pm$ pairs and x-rays; magnetics and nozzles collimate the hot plasma outward. Engineering hell, but momentum accounting likes it.

3) A “gravitational flywheel.”
Black holes have only three knobs—mass $M$, spin $J$, charge $Q$. 

You can spin it up by feeding it orbital angular momentum (beams/pellets on prograde, off-axis trajectories) and later extract some of that rotational energy via superradiance (certain waves reflect with more energy than they came in with) or via magnetized-plasma analogs of Blandford–Znajek. In effect: a compact, ridiculous-energy-density flywheel.

4) A precision gravity lab / time-dilation rig.

At meter scales the field is strong enough for exquisite redshift and clock-comparison experiments, equivalence-principle tests, and probe dynamics in steep potentials. 
You’d keep everything in ultra-high vacuum and use active station-keeping so the lab doesn’t “fall onto” the hole.

5) A waste-to-energy terminus.

Drop junk in; you recover a (tiny) fraction of the rest mass as Hawking heat. Realistically you’d only “profit” if you already need the radiation source for 1–3. It’s not a green recycler so much as a very final end-of-life shredder.

6) A high-frequency gravitational-wave bell.

Kick it and it “rings” in quasinormal modes at frequencies $f \sim \frac{c^3}{GM}$. For this mass, that’s $\sim 10^{22}$ Hz (gamma-ray energies), i.e., far beyond today’s GW bands. It’s still a pristine arena to test the math of ringdowns and horizon physics.


A micro-BH is the ultimate universal incinerator + energy store, but it’s a radiological nightmare and insane control problem.

Antimatter, pulsed fusion, and fission-fragment systems beat it when you want usable power and thrust without MeV-gamma hell—and beamed power beats all of them whenever you can build infrastructure.

If you do use a BH as a battery, essentially all mass-energy you add is recoverable as radiation (no leftover core), with an unavoidable neutrino haircut and real-world conversion losses.

</div>