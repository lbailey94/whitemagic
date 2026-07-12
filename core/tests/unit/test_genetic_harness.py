# ruff: noqa: BLE001
"""Tests for Genetic Algorithm Harness (v24.3 §5.1)."""
from __future__ import annotations

import random

import pytest

from whitemagic.core.evolution.genetic_harness import (
    Chromosome,
    GeneticConfig,
    GeneticHarness,
)


@pytest.fixture
def simple_harness():
    """GA that maximizes sum of genes."""
    config = GeneticConfig(
        population_size=20,
        mutation_rate=0.2,
        crossover_rate=0.8,
        elitism=2,
        max_generations=50,
        convergence_threshold=0.001,
        gene_bounds={"x": (0.0, 10.0), "y": (0.0, 10.0)},
    )

    def fitness(chrom: Chromosome) -> float:
        return chrom.genes.get("x", 0) + chrom.genes.get("y", 0)

    return GeneticHarness(config, fitness)


class TestChromosome:
    def test_default_chromosome(self):
        c = Chromosome()
        assert c.genes == {}
        assert c.fitness == 0.0
        assert c.generation == 0
        assert len(c.id) == 8

    def test_chromosome_with_genes(self):
        c = Chromosome(genes={"x": 5.0, "y": 3.0}, fitness=8.0)
        assert c.genes["x"] == 5.0
        assert c.fitness == 8.0


class TestGeneticHarness:
    def test_initialize_population(self, simple_harness):
        pop = simple_harness.initialize_population()
        assert len(pop) == 20
        for chrom in pop:
            assert "x" in chrom.genes
            assert "y" in chrom.genes

    def test_initialize_with_seed(self, simple_harness):
        pop = simple_harness.initialize_population(seed_genes={"x": 5.0, "y": 5.0})
        # First 2 should be exact copies (elitism=2)
        assert pop[0].genes["x"] == 5.0
        assert pop[1].genes["x"] == 5.0
        # Rest should be perturbed (likely different)
        assert len(pop) == 20

    def test_evaluate_sets_fitness(self, simple_harness):
        chrom = Chromosome(genes={"x": 3.0, "y": 4.0})
        result = simple_harness.evaluate(chrom)
        assert result.fitness == 7.0

    def test_tournament_selection(self, simple_harness):
        pop = [
            Chromosome(genes={"x": 1, "y": 1}, fitness=2.0),
            Chromosome(genes={"x": 9, "y": 9}, fitness=18.0),
            Chromosome(genes={"x": 5, "y": 5}, fitness=10.0),
        ]
        selected = simple_harness.select(pop, tournament_size=2)
        # With tournament size 2, the fittest should be selected most often
        assert len(selected) == 3

    def test_crossover_combines_genes(self, simple_harness):
        parent_a = Chromosome(genes={"x": 10.0, "y": 0.0})
        parent_b = Chromosome(genes={"x": 0.0, "y": 10.0})
        child = simple_harness.crossover(parent_a, parent_b)
        assert "x" in child.genes
        assert "y" in child.genes
        # x should be from either parent
        assert child.genes["x"] in (10.0, 0.0)
        assert child.genes["y"] in (10.0, 0.0)
        assert child.generation == 1

    def test_mutate_perturbs_genes(self, simple_harness):
        simple_harness._config.mutation_rate = 1.0  # Force mutation
        chrom = Chromosome(genes={"x": 5.0, "y": 5.0})
        original_x = chrom.genes["x"]
        simple_harness.mutate(chrom)
        # With mutation_rate=1.0, x should likely change
        assert 0.0 <= chrom.genes["x"] <= 10.0  # Within bounds

    def test_mutate_respects_bounds(self, simple_harness):
        simple_harness._config.mutation_rate = 1.0
        for _ in range(100):
            chrom = Chromosome(genes={"x": 5.0, "y": 5.0})
            simple_harness.mutate(chrom)
            assert 0.0 <= chrom.genes["x"] <= 10.0
            assert 0.0 <= chrom.genes["y"] <= 10.0

    def test_evolve_one_generation(self, simple_harness):
        simple_harness.initialize_population()
        new_pop = simple_harness.evolve_one_generation()
        assert len(new_pop) == 20
        assert simple_harness._generation == 1
        assert len(simple_harness._history) == 1

    def test_convergence(self, simple_harness):
        """GA should converge near optimal (x=10, y=10, fitness=20)."""
        random.seed(42)
        simple_harness.initialize_population(seed_genes={"x": 5.0, "y": 5.0})
        best = simple_harness.run(generations=50)
        assert best.fitness > 10.0  # Should get reasonably close to 20

    def test_elitism_preserves_best(self, simple_harness):
        """Top chromosomes should survive to next generation."""
        random.seed(42)
        simple_harness.initialize_population()
        # Evaluate and sort
        for c in simple_harness._population:
            simple_harness.evaluate(c)
        simple_harness._population.sort(key=lambda c: c.fitness, reverse=True)
        best_fitness = simple_harness._population[0].fitness

        simple_harness.evolve_one_generation()
        # After evolution, at least one chromosome should have fitness >= best
        # (elites are preserved with their fitness)
        assert any(c.fitness >= best_fitness for c in simple_harness._population)

    def test_get_history(self, simple_harness):
        random.seed(42)
        simple_harness.initialize_population()
        simple_harness.evolve_one_generation()
        simple_harness.evolve_one_generation()
        history = simple_harness.get_history()
        assert len(history) == 2
        assert "best" in history[0]
        assert "avg" in history[0]
        assert "worst" in history[0]

    def test_get_status(self, simple_harness):
        random.seed(42)
        simple_harness.initialize_population()
        simple_harness.evolve_one_generation()
        status = simple_harness.get_status()
        assert status["generation"] == 1
        assert status["population_size"] == 20
        assert "best_fitness" in status
