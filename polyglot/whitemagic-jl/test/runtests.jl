using Test

# Ensure module is loadable
push!(LOAD_PATH, joinpath(@__DIR__, "..", "src"))
using HolographicMemory: encode_5d, zone_of, euclidean_5d, nearest_neighbors,
                         constellation_detect, holographic_hash, coherence_score

@testset "HolographicMemory" begin
    @testset "encode_5d" begin
        c = encode_5d("hello world")
        @test length(c) == 5
        @test all(x -> isa(x, Float64), c)
        @test encode_5d("hello world") == encode_5d("hello world")
    end

    @testset "zone_of" begin
        @test zone_of((0.0, 0.0, 0.0, 0.0, 0.1)) == "CORE"
        @test zone_of((0.0, 0.0, 0.0, 0.0, 0.3)) == "INNER_RING"
        @test zone_of((0.0, 0.0, 0.0, 0.0, 0.5)) == "MID_RING"
        @test zone_of((0.0, 0.0, 0.0, 0.0, 0.7)) == "OUTER_RING"
        @test zone_of((0.0, 0.0, 0.0, 0.0, 0.9)) == "FAR_EDGE"
    end

    @testset "euclidean_5d" begin
        a = (1.0, 0.0, 0.0, 0.0, 0.0)
        b = (4.0, 0.0, 0.0, 0.0, 0.0)
        @test euclidean_5d(a, b) ≈ 3.0
    end

    @testset "nearest_neighbors" begin
        pts = [(i * 1.0, 0.0, 0.0, 0.0, 0.0) for i in 0:9]
        q = (4.5, 0.0, 0.0, 0.0, 0.0)
        nn = nearest_neighbors(q, pts, 3)
        @test length(nn) == 3
        @test nn[1][1] == 5  # Julia is 1-indexed, index 5 = value 4.0
    end

    @testset "constellation_detect" begin
        pts = [
            (0.0, 0.0, 0.0, 0.0, 0.0),
            (0.1, 0.0, 0.0, 0.0, 0.0),
            (0.2, 0.0, 0.0, 0.0, 0.0),
            (10.0, 0.0, 0.0, 0.0, 0.0),
            (10.1, 0.0, 0.0, 0.0, 0.0),
        ]
        clusters = constellation_detect(pts, threshold=0.8, min_size=2)
        @test length(clusters) == 2
    end

    @testset "holographic_hash" begin
        c = encode_5d("test")
        h = holographic_hash(c, bins_per_dim=8)
        @test h isa String
        @test length(h) > 0
    end

    @testset "coherence_score" begin
        pts = [encode_5d("memory $i") for i in 1:5]
        score = coherence_score(pts)
        @test 0.0 <= score <= 1.0
    end
end

println("All tests passed!")
