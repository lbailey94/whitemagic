using Test
using LinearAlgebra
using Statistics

# Include the module directly
include("../src/GalaxyComparison.jl")
using .GalaxyComparison

@testset "GalaxyComparison" begin
    
    @testset "compute_galaxy_stats" begin
        importance = [0.5, 0.8, 0.3, 0.9, 0.6]
        coords = [0.1 0.5 0.3 0.7 0.2;
                  0.2 0.4 0.6 0.1 0.3;
                  0.5 0.3 0.7 0.2 0.4;
                  0.6 0.1 0.8 0.3 0.5;
                  0.7 0.9 0.1 0.4 0.6]
        stats = compute_galaxy_stats("test", importance, coords)
        @test stats.galaxy_id == "test"
        @test stats.n_memories == 5
        @test stats.mean_importance ≈ 0.62 atol=0.01
        @test stats.min_importance == 0.3
        @test stats.max_importance == 0.9
    end
    
    @testset "compute_galaxy_stats empty" begin
        stats = compute_galaxy_stats("empty", Float64[], zeros(5, 0))
        @test stats.n_memories == 0
        @test stats.mean_importance == 0.0
    end
    
    @testset "ks_statistic identical" begin
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        d, p = ks_statistic(a, a)
        @test d ≈ 0.0 atol=0.01
        @test p > 0.9  # High p-value for identical distributions
    end
    
    @testset "ks_statistic different" begin
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [10.0, 20.0, 30.0, 40.0, 50.0]
        d, p = ks_statistic(a, b)
        @test d > 0.5  # Large D for very different distributions
        @test p < 0.5  # Low p-value
    end
    
    @testset "ks_statistic empty" begin
        d, p = ks_statistic(Float64[], Float64[])
        @test d == 0.0
        @test p == 1.0
    end
    
    @testset "js_divergence identical" begin
        p = [1.0, 2.0, 3.0, 4.0]
        jsd = js_divergence(p, p)
        @test jsd ≈ 0.0 atol=0.01
    end
    
    @testset "js_divergence different" begin
        p = [10.0, 0.0, 0.0, 0.0]
        q = [0.0, 0.0, 0.0, 10.0]
        jsd = js_divergence(p, q)
        @test jsd > 0.5  # High divergence for disjoint distributions
    end
    
    @testset "js_divergence empty" begin
        jsd = js_divergence(Float64[], Float64[])
        @test jsd == 0.0
    end
    
    @testset "emd_estimate identical" begin
        a = [1.0, 2.0, 3.0]
        emd = emd_estimate(a, a)
        @test emd ≈ 0.0 atol=0.01
    end
    
    @testset "emd_estimate different" begin
        a = [1.0, 2.0, 3.0]
        b = [10.0, 20.0, 30.0]
        emd = emd_estimate(a, b)
        @test emd > 5.0  # Large EMD for different distributions
    end
    
    @testset "galaxy_density" begin
        # Dense cluster
        coords_dense = [0.1 0.2 0.15 0.12 0.18;
                        0.1 0.2 0.15 0.12 0.18;
                        0.1 0.2 0.15 0.12 0.18;
                        0.1 0.2 0.15 0.12 0.18;
                        0.1 0.2 0.15 0.12 0.18]
        d = galaxy_density(coords_dense, 0.5)
        @test d > 0.5  # High density for clustered points
        
        # Sparse
        coords_sparse = [0.0 10.0 20.0 30.0 40.0;
                         0.0 10.0 20.0 30.0 40.0;
                         0.0 10.0 20.0 30.0 40.0;
                         0.0 10.0 20.0 30.0 40.0;
                         0.0 10.0 20.0 30.0 40.0]
        d_sparse = galaxy_density(coords_sparse, 0.5)
        @test d_sparse ≈ 0.0 atol=0.01
    end
    
    @testset "cross_galaxy_correlation" begin
        stats_a = GalaxyStats("a", 10, 0.5, 0.1, 0.1, 0.2, 0.3, 0.4, 0.5, 0.1, 0.9)
        stats_b = GalaxyStats("b", 10, 0.5, 0.1, 0.1, 0.2, 0.3, 0.4, 0.5, 0.1, 0.9)
        corr = cross_galaxy_correlation(stats_a, stats_b)
        @test corr ≈ 1.0 atol=0.01  # Identical stats → perfect correlation
        
        # Orthogonal
        stats_c = GalaxyStats("c", 10, 0.5, 0.1, 1.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.9)
        stats_d = GalaxyStats("d", 10, 0.5, 0.1, 0.0, 1.0, 0.0, 0.0, 0.0, 0.1, 0.9)
        corr2 = cross_galaxy_correlation(stats_c, stats_d)
        @test corr2 < 0.5
    end
    
    @testset "compare_galaxies full" begin
        imp_a = [0.5, 0.6, 0.7, 0.8, 0.55, 0.65]
        coords_a = [0.1 0.2 0.3 0.15 0.25 0.12;
                    0.5 0.6 0.4 0.55 0.45 0.5;
                    0.3 0.4 0.2 0.35 0.25 0.3;
                    0.7 0.6 0.8 0.65 0.75 0.7;
                    0.5 0.6 0.7 0.55 0.65 0.5]
        
        imp_b = [0.1, 0.2, 0.15, 0.25, 0.12, 0.18]
        coords_b = [0.8 0.9 0.85 0.75 0.82 0.88;
                    0.1 0.2 0.15 0.05 0.12 0.18;
                    0.9 0.8 0.85 0.75 0.82 0.88;
                    0.1 0.2 0.15 0.05 0.12 0.18;
                    0.1 0.2 0.15 0.25 0.12 0.18]
        
        result = compare_galaxies("galaxy_a", imp_a, coords_a, "galaxy_b", imp_b, coords_b)
        
        @test result.galaxy_a == "galaxy_a"
        @test result.galaxy_b == "galaxy_b"
        @test result.ks_statistic >= 0.0
        @test result.js_divergence >= 0.0
        @test result.emd_estimate >= 0.0
        @test length(result.summary) > 0
    end
end
