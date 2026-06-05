defmodule WhiteMagicElixir.CoordinateTest do
  use ExUnit.Case

  alias WhiteMagicElixir.Coordinate

  test "new creates a coordinate with default values" do
    c = Coordinate.new()
    assert c.x == 0.0
    assert c.v == 0.0
  end

  test "new clamps w and v to [0,1]" do
    c = Coordinate.new(0, 0, 0, 1.5, -0.1)
    assert c.w == 1.0
    assert c.v == 0.0
  end

  test "encode is deterministic" do
    c1 = Coordinate.encode("hello world")
    c2 = Coordinate.encode("hello world")
    assert c1 == c2
  end

  test "encode produces different coords for different texts" do
    c1 = Coordinate.encode("hello")
    c2 = Coordinate.encode("world")
    assert c1 != c2
  end

  test "distance is symmetric and non-negative" do
    a = Coordinate.new(0, 0, 0, 0, 0)
    b = Coordinate.new(1, 1, 1, 1, 1)
    d = Coordinate.distance(a, b)
    assert d >= 0
    assert Coordinate.distance(b, a) == d
  end

  test "zone mapping" do
    assert Coordinate.zone(%Coordinate{x: 0, y: 0, z: 0, w: 0, v: 0.1}) == "CORE"
    assert Coordinate.zone(%Coordinate{x: 0, y: 0, z: 0, w: 0, v: 0.5}) == "MID_RING"
    assert Coordinate.zone(%Coordinate{x: 0, y: 0, z: 0, w: 0, v: 0.9}) == "FAR_EDGE"
  end

  test "merge computes centroid" do
    a = Coordinate.new(0, 0, 0, 0, 0)
    b = Coordinate.new(2, 2, 2, 1, 1)
    c = Coordinate.merge([a, b])
    assert c.x == 1.0
    assert c.v == 0.5
  end

  test "coherence of identical points is 1.0" do
    points = List.duplicate(Coordinate.new(1, 1, 1, 0.5, 0.5), 5)
    assert Coordinate.coherence(points) == 1.0
  end

  test "encode empty text returns zero coordinate" do
    c = Coordinate.encode("")
    assert c.x == 0.0
    assert c.y == 0.0
    assert c.z == 0.0
    assert c.w == 0.0
    assert c.v == 0.0
  end

  test "distance exact value" do
    a = Coordinate.new(1, 0, 0, 0, 0)
    b = Coordinate.new(4, 0, 0, 0, 0)
    assert_in_delta Coordinate.distance(a, b), 3.0, 1.0e-9
  end

  test "lsh returns string hash" do
    c = Coordinate.encode("test")
    h = Coordinate.lsh(c, 8)
    assert is_binary(h)
    assert String.starts_with?(h, "H")
  end
end
