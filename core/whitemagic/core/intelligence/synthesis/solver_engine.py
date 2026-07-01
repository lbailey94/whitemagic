# ruff: noqa: BLE001
"""Dharmic Solver Engine — cvxpy-based constrained optimization."""

from __future__ import annotations

import logging

import numpy as np

try:
    import cvxpy as cp

    HAS_CVXPY = True
except ImportError:
    HAS_CVXPY = False
    cp = None  # type: ignore[misc]

logger = logging.getLogger(__name__)


class DharmicSolver:
    """Dharmic Solver — Layer 3: Optimization.

    Solves for the optimal configuration of concepts/actions.

    Goal: Maximize Relevance while respecting Causal DAG constraints.
    """

    def solve(
        self,
        nodes: list[str],
        edges: list[tuple[str, str]],
        scores: dict[str, float],
        budget: int | None = None,
        max_iters: int = 50,
        lambda_reg: float = 0.01,
    ) -> list[str]:
        """Solve the constrained optimization problem using Frank-Wolfe.

        Objective: Maximize scores^T x - lambda * sum(x_i * log(x_i))
        Subject to: x in Marginal Polytope (0 <= x_j <= x_i <= 1)
        """
        n = len(nodes)
        if n == 0:
            return []
        node_to_idx = {node: i for i, node in enumerate(nodes)}

        # Default budget: 1/3 of nodes or min(10, n)
        if budget is None:
            budget = min(10, n // 3 + 1)

        # 1. Initialize continuous selection vector (Marginal Polytope)
        x = np.zeros(n)
        relevance = np.array([scores.get(node, 0.0) for node in nodes])

        # 2. Entropy-Regularized Frank-Wolfe Loop
        logger.info(
            "DharmicSolver: Starting Frank-Wolfe optimization for %s nodes (budget: %s)",
            n,
            budget,
        )
        t = 0
        for t in range(max_iters):
            # Gradient: scores - lambda * (log(x) + 1)
            # We use a smoothed gradient to avoid log(0)
            grad = relevance - lambda_reg * (np.log(x + 1e-10) + 1)

            # Linear Minimization Oracle (LMO)
            s_best = self._linear_oracle(nodes, edges, node_to_idx, grad, budget)

            gamma = 2.0 / (t + 2.0)

            # Update
            new_x = x + gamma * (s_best - x)

            if np.linalg.norm(new_x - x) < 1e-6:
                x = new_x
                break
            x = new_x

        # 3. Final Projection / Thresholding
        # Budget-Aware Rounding: sort by value and take top 'budget' nodes if > epsilon
        indexed_values = sorted(
            [(x[i], nodes[i]) for i in range(n)],
            key=lambda p: p[0],
            reverse=True,
        )
        selected = [node for val, node in indexed_values[:budget] if val > 0.1]

        logger.info(
            "DharmicSolver: Selected %s nodes after %s iterations",
            len(selected),
            t + 1,
        )
        return selected

    def _linear_oracle(
        self,
        nodes: list[str],
        edges: list[tuple[str, str]],
        node_to_idx: dict[str, int],
        grad: np.ndarray,
        budget: int,
    ) -> np.ndarray:
        """Linear Minimization Oracle over the Marginal Polytope.

        Uses CVXPY if available, otherwise falls back to greedy numpy.
        """
        n = len(nodes)

        # Fallback: Greedy selection respecting constraints
        if not HAS_CVXPY:
            s = np.zeros(n)
            sorted_indices = np.argsort(-grad)
            selected_count = 0
            selected_set: set[str] = set()

            for idx in sorted_indices:
                if selected_count >= budget:
                    break

                node = nodes[idx]
                can_select = True

                for parent, child in edges:
                    if child == node and parent not in selected_set:
                        can_select = False
                        break

                if can_select:
                    s[idx] = 1.0
                    selected_set.add(node)
                    selected_count += 1

            return s

        # CVXPY implementation
        s = cp.Variable(n)  # type: ignore[misc]

        # Objective: Maximize grad^T s
        objective = cp.Maximize(grad @ s)  # type: ignore[misc]

        constraints = [s >= 0, s <= 1]

        # Budget constraint
        constraints.append(cp.sum(s) <= budget)  # type: ignore[misc]

        # Causal constraints: s_child <= s_parent
        for parent, child in edges:
            if parent in node_to_idx and child in node_to_idx:
                constraints.append(s[node_to_idx[child]] <= s[node_to_idx[parent]])

        prob = cp.Problem(objective, constraints)  # type: ignore[misc]
        try:
            prob.solve(
                solver=cp.GLPK_MI if "GLPK_MI" in cp.installed_solvers() else None,  # type: ignore[misc]
                verbose=False,
            )
        except Exception as e:
            logger.debug("CVXPY solve failed, falling back to greedy: %s", e)
            return self._linear_oracle(nodes, edges, node_to_idx, grad, budget)

        if s.value is None:
            return np.zeros(n)
        return s.value  # type: ignore[no-any-return]


_solver: DharmicSolver | None = None


def get_dharmic_solver() -> DharmicSolver:
    """Get the global DharmicSolver instance."""
    global _solver
    if _solver is None:
        _solver = DharmicSolver()
    return _solver
