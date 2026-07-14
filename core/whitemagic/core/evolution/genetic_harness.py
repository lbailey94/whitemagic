# ruff: noqa: BLE001
"""Genetic Algorithm Harness — Evolutionary parameter optimization.
================================================================
Population-based optimization using tournament selection,
uniform crossover, and bounded mutation. Suited for discrete
parameter optimization (model configs, tool weights, etc.).

Usage::

    from whitemagic.core.evolution.genetic_harness import GeneticHarness, GeneticConfig

    def fitness(chrom):
        return sum(chrom.genes.values())

    harness = GeneticHarness(GeneticConfig(
        gene_bounds={"x": (0, 10), "y": (0, 10)},
    ), fitness)
    best = harness.run(generations=50)
    print(f"Best fitness: {best.fitness}, genes: {best.genes}")
"""
from __future__ import annotations

import logging
import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────


@dataclass
class Chromosome:
    """An individual in the population."""

    genes: dict[str, Any] = field(default_factory=dict)
    fitness: float = 0.0
    generation: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    parent_ids: list[str] = field(default_factory=list)


@dataclass
class GeneticConfig:
    """Configuration for the genetic algorithm."""

    population_size: int = 20
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    elitism: int = 2  # top N preserved unchanged
    max_generations: int = 50
    convergence_threshold: float = 0.01  # stop if improvement < this
    gene_bounds: dict[str, tuple[float, float]] = field(default_factory=dict)


# ── Genetic Harness ──────────────────────────────────────────────────


class GeneticHarness:
    """Population-based genetic algorithm optimizer."""

    def __init__(
        self,
        config: GeneticConfig,
        fitness_fn: Callable[[Chromosome], float],
    ) -> None:
        self._config = config
        self._fitness_fn = fitness_fn
        self._population: list[Chromosome] = []
        self._generation: int = 0
        self._history: list[dict[str, float]] = []  # best/avg/worst per generation

    def initialize_population(self, seed_genes: dict[str, Any] | None = None) -> list[Chromosome]:
        """Create the initial population."""
        pop: list[Chromosome] = []
        for i in range(self._config.population_size):
            if seed_genes and i < self._config.elitism:
                # First few are exact copies of seed
                genes = dict(seed_genes)
            elif seed_genes:
                # Rest are variations of seed
                genes = self._perturb(seed_genes)
            else:
                genes = self._random_genes()
            pop.append(Chromosome(genes=genes, generation=0))
        self._population = pop
        return pop

    def evaluate(self, chromosome: Chromosome) -> Chromosome:
        """Evaluate fitness and return the chromosome."""
        chromosome.fitness = self._fitness_fn(chromosome)
        return chromosome

    def select(self, population: list[Chromosome], tournament_size: int = 3) -> list[Chromosome]:
        """Tournament selection — pick best from random subsets."""
        selected: list[Chromosome] = []
        pop_size = len(population)
        for _ in range(pop_size):
            contestants = random.sample(population, min(tournament_size, pop_size))
            winner = max(contestants, key=lambda c: c.fitness)
            selected.append(winner)
        return selected

    def crossover(self, parent_a: Chromosome, parent_b: Chromosome) -> Chromosome:
        """Uniform crossover — each gene randomly from A or B."""
        if random.random() > self._config.crossover_rate:
            # No crossover — return copy of parent A
            return Chromosome(
                genes=dict(parent_a.genes),
                generation=self._generation + 1,
                parent_ids=[parent_a.id],
            )

        child_genes: dict[str, Any] = {}
        all_keys = set(parent_a.genes.keys()) | set(parent_b.genes.keys())
        for key in all_keys:
            if key in parent_a.genes and key in parent_b.genes:
                child_genes[key] = random.choice([parent_a.genes[key], parent_b.genes[key]])
            elif key in parent_a.genes:
                child_genes[key] = parent_a.genes[key]
            else:
                child_genes[key] = parent_b.genes[key]

        return Chromosome(
            genes=child_genes,
            generation=self._generation + 1,
            parent_ids=[parent_a.id, parent_b.id],
        )

    def mutate(self, chromosome: Chromosome) -> Chromosome:
        """Mutate genes with probability mutation_rate, within bounds."""
        for gene_name, (lo, hi) in self._config.gene_bounds.items():
            if gene_name not in chromosome.genes:
                continue
            if random.random() < self._config.mutation_rate:
                current = chromosome.genes[gene_name]
                if isinstance(current, int):
                    chromosome.genes[gene_name] = int(random.uniform(lo, hi))
                else:
                    # Gaussian perturbation around current, clamped to bounds
                    sigma = (hi - lo) * 0.1
                    new_val = random.gauss(current, sigma)
                    chromosome.genes[gene_name] = max(lo, min(hi, new_val))
        return chromosome

    def evolve_one_generation(self) -> list[Chromosome]:
        """Run one generation: evaluate → select → crossover → mutate."""
        # Evaluate all
        for chrom in self._population:
            self.evaluate(chrom)

        # Sort by fitness
        self._population.sort(key=lambda c: c.fitness, reverse=True)

        # Record stats
        best = self._population[0].fitness
        avg = sum(c.fitness for c in self._population) / len(self._population)
        worst = self._population[-1].fitness
        self._history.append({"best": best, "avg": avg, "worst": worst})

        # Elitism — preserve top N
        elites = [Chromosome(
            genes=dict(c.genes),
            fitness=c.fitness,
            generation=self._generation + 1,
            parent_ids=[c.id],
        ) for c in self._population[:self._config.elitism]]

        # Selection
        selected = self.select(self._population)

        # Crossover + mutation to fill rest
        new_pop: list[Chromosome] = list(elites)
        while len(new_pop) < self._config.population_size:
            parent_a = random.choice(selected)
            parent_b = random.choice(selected)
            child = self.crossover(parent_a, parent_b)
            child = self.mutate(child)
            new_pop.append(child)

        self._population = new_pop
        self._generation += 1
        return self._population

    def run(self, generations: int | None = None) -> Chromosome:
        """Run the GA until convergence or max generations."""
        if not self._population:
            self.initialize_population()

        max_gen = generations or self._config.max_generations
        for _ in range(max_gen):
            self.evolve_one_generation()

            # Check convergence
            if len(self._history) >= 2:
                improvement = abs(self._history[-1]["best"] - self._history[-2]["best"])
                if (
                    self._history[-2]["best"] != 0
                    and improvement / abs(self._history[-2]["best"]) < self._config.convergence_threshold
                ):
                    logger.info("GA converged at generation %d", self._generation)
                    break

        # Final evaluation
        for chrom in self._population:
            self.evaluate(chrom)
        self._population.sort(key=lambda c: c.fitness, reverse=True)
        return self._population[0]

    def get_history(self) -> list[dict[str, float]]:
        """Return per-generation fitness statistics."""
        return self._history

    def get_status(self) -> dict[str, Any]:
        """Return GA status for MCP tool."""
        return {
            "generation": self._generation,
            "population_size": len(self._population),
            "config": {
                "mutation_rate": self._config.mutation_rate,
                "crossover_rate": self._config.crossover_rate,
                "elitism": self._config.elitism,
                "max_generations": self._config.max_generations,
            },
            "history_length": len(self._history),
            "best_fitness": self._history[-1]["best"] if self._history else 0.0,
        }

    # ── Internal helpers ──

    def _random_genes(self) -> dict[str, Any]:
        """Generate random genes within bounds."""
        genes: dict[str, Any] = {}
        for name, (lo, hi) in self._config.gene_bounds.items():
            genes[name] = random.uniform(lo, hi)
        return genes

    def _perturb(self, seed: dict[str, Any]) -> dict[str, Any]:
        """Create a perturbed variation of seed genes."""
        genes = dict(seed)
        for name, (lo, hi) in self._config.gene_bounds.items():
            if name in genes:
                sigma = (hi - lo) * 0.2
                genes[name] = max(lo, min(hi, random.gauss(genes[name], sigma)))
        return genes
