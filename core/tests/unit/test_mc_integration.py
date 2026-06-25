"""Tests for MC-HLL/CMS integration."""
from whitemagic.forecasting.mc_integration import MCForecastEnhancer


def _make_claims(n: int = 10, duplicates: int = 0) -> list[dict]:
    """Generate test claims with optional duplicates."""
    claims = []
    for i in range(n):
        claims.append({
            "id": f"claim_{i}",
            "claim": f"Prediction number {i} about AI governance",
            "confidence": 0.7 + (i % 3) * 0.1,
            "outcome": 1.0 if i % 3 != 2 else 0.0,
            "lead_weeks": float(10 + i),
            "category": "ai_governance" if i % 2 == 0 else "ai_hardware",
            "status": "validated" if i % 3 != 2 else "falsified",
            "source_ref": f"ref_{i}",
        })
    # Add exact duplicates
    for i in range(duplicates):
        claims.append(claims[i % n].copy())
    return claims


class TestClaimAnalytics:
    def test_observe_claims_basic(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        analytics = enhancer.observe_claims(claims)
        assert analytics.total_claims == 10
        assert analytics.distinct_estimates > 0
        assert analytics.duplicate_ratio < 0.1  # No duplicates

    def test_duplicate_detection(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10, duplicates=5)
        analytics = enhancer.observe_claims(claims)
        assert analytics.total_claims == 15
        # HLL should detect that there are fewer distinct claims
        assert analytics.distinct_estimates <= 12  # Allow HLL error margin
        assert analytics.duplicate_ratio > 0.1

    def test_category_cardinality(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        analytics = enhancer.observe_claims(claims)
        assert "ai_governance" in analytics.category_cardinality
        assert "ai_hardware" in analytics.category_cardinality

    def test_frequency_distribution(self):
        enhancer = MCForecastEnhancer()
        # Observe same claims multiple times to build CMS frequency
        claims = _make_claims(n=5)
        for _ in range(15):
            enhancer.observe_claims(claims)
        analytics = enhancer.observe_claims(claims)
        # After 16 observations, all claims should be "high" frequency
        assert analytics.frequency_distribution["high"] == 5


class TestDeduplication:
    def test_deduplicate_removes_exact_duplicates(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10, duplicates=3)
        unique = enhancer.deduplicate_claims(claims)
        assert len(unique) == 10

    def test_deduplicate_preserves_unique(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10, duplicates=0)
        unique = enhancer.deduplicate_claims(claims)
        assert len(unique) == 10


class TestAdaptiveTrials:
    def test_high_frequency_gets_more_trials(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=5)
        # Observe many times to build high frequency
        for _ in range(20):
            enhancer.observe_claims(claims)

        trials = enhancer.get_adaptive_trials("claim_0")
        assert trials >= 10000  # Should be high tier (20000)

    def test_low_frequency_gets_fewer_trials(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=5)
        enhancer.observe_claims(claims)  # Single observation

        trials = enhancer.get_adaptive_trials("claim_0")
        assert trials <= 10000  # Should be low or medium tier

    def test_unknown_claim_gets_default(self):
        enhancer = MCForecastEnhancer()
        trials = enhancer.get_adaptive_trials("unknown_claim", default=5000)
        assert trials == 5000


class TestRunCalibrated:
    def test_run_with_rust_or_python(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        result = enhancer.run_calibrated(claims, n_trials=100)
        assert "mc_result" in result
        assert "analytics" in result
        mc = result["mc_result"]
        assert mc["n_trials"] == 100
        assert mc["n_claims"] == 10
        assert "brier_score" in mc
        assert "brier_skill_score" in mc

    def test_run_with_deduplication(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10, duplicates=5)
        result = enhancer.run_calibrated(claims, n_trials=100, deduplicate=True)
        # After dedup, n_claims should be 10 not 15
        assert result["mc_result"]["n_claims"] == 10
        assert result["analytics"]["duplicate_ratio"] > 0.1

    def test_run_without_deduplication(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10, duplicates=5)
        result = enhancer.run_calibrated(claims, n_trials=100, deduplicate=False)
        # All 15 claims passed through
        assert result["mc_result"]["n_claims"] == 15

    def test_analytics_metadata_complete(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        result = enhancer.run_calibrated(claims, n_trials=100)
        analytics = result["analytics"]
        assert "total_claims" in analytics
        assert "distinct_claims" in analytics
        assert "duplicate_ratio" in analytics
        assert "category_cardinality" in analytics
        assert "frequency_distribution" in analytics
        assert "total_adaptive_trials" in analytics


class TestVarianceReduction:
    """Tests for Objective E — Multi-Round MC with Variance Reduction."""

    def test_antithetic_basic(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        result = enhancer._run_python_mc_antithetic(claims, n_trials=100)
        assert result["n_trials"] == 100
        assert result["n_claims"] == 10
        assert result["variance_reduction"] == "antithetic"
        assert "brier_score" in result
        assert "std_dev" in result["brier_score"]

    def test_antithetic_no_resolved(self):
        enhancer = MCForecastEnhancer()
        claims = [{"id": "x", "confidence": 0.7, "outcome": None, "status": "pending"}]
        result = enhancer._run_python_mc_antithetic(claims, n_trials=100)
        assert "error" in result

    def test_antithetic_odd_trials(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=5)
        result = enhancer._run_python_mc_antithetic(claims, n_trials=101)
        assert result["n_trials"] == 101
        assert "brier_score" in result

    def test_control_variate_basic(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        result = enhancer._run_python_mc_control_variate(claims, n_trials=100)
        assert result["n_trials"] == 100
        assert result["variance_reduction"] == "control_variate"
        assert "brier_score" in result

    def test_control_variate_no_resolved(self):
        enhancer = MCForecastEnhancer()
        claims = [{"id": "x", "confidence": 0.7, "outcome": None, "status": "pending"}]
        result = enhancer._run_python_mc_control_variate(claims, n_trials=100)
        assert "error" in result

    def test_run_calibrated_vr_antithetic(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        result = enhancer.run_calibrated_vr(claims, n_trials=100, method="antithetic")
        assert "mc_result" in result
        assert "analytics" in result
        assert "variance_reduction" in result["mc_result"]

    def test_run_calibrated_vr_control_variate(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        result = enhancer.run_calibrated_vr(claims, n_trials=100, method="control_variate")
        assert "mc_result" in result
        assert "variance_reduction" in result["mc_result"]

    def test_run_calibrated_vr_with_dedup(self):
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10, duplicates=5)
        result = enhancer.run_calibrated_vr(claims, n_trials=100, deduplicate=True)
        assert result["mc_result"]["n_claims"] == 10

    def test_antithetic_lower_variance_than_plain(self):
        """Antithetic variates should produce lower or equal variance vs plain MC."""
        import random
        random.seed(42)
        enhancer1 = MCForecastEnhancer()
        claims = _make_claims(n=20)
        plain = enhancer1._run_python_mc(claims, n_trials=200)

        random.seed(42)
        enhancer2 = MCForecastEnhancer()
        anti = enhancer2._run_python_mc_antithetic(claims, n_trials=200)

        # Antithetic should have lower or similar variance (allowing noise)
        plain_std = plain["brier_score"]["std_dev"]
        anti_std = anti["brier_score"]["std_dev"]
        # Antithetic should not be dramatically worse
        assert anti_std <= plain_std * 1.5


class TestCorrelatedMC:
    """Tests for Objective B — Interaction-Aware Monte Carlo."""

    def test_correlated_mc_no_matrix(self):
        """Without correlation matrix, should fall back to independent MC."""
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=10)
        result = enhancer.run_correlated_mc(claims, correlation_matrix=None, n_trials=100)
        assert result["n_trials"] == 100
        assert "brier_score" in result

    def test_correlated_mc_with_matrix(self):
        """With correlation matrix, should produce correlation-aware results."""
        enhancer = MCForecastEnhancer()
        claims = _make_claims(n=5)
        # Build a simple correlation matrix
        claim_ids = [c["id"] for c in claims]
        matrix = {}
        for a in claim_ids:
            matrix[a] = {}
            for b in claim_ids:
                matrix[a][b] = 0.5 if a != b else 1.0
        result = enhancer.run_correlated_mc(claims, correlation_matrix=matrix, n_trials=100)
        assert result["correlation_aware"] is True
        assert "brier_score" in result

    def test_correlated_mc_no_resolved(self):
        enhancer = MCForecastEnhancer()
        claims = [{"id": "x", "confidence": 0.7, "outcome": None, "status": "pending"}]
        result = enhancer.run_correlated_mc(claims, correlation_matrix={}, n_trials=100)
        assert "error" in result
