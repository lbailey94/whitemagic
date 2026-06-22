module WhiteMagic.Holographic
  ( Coordinate5D(..)
  , zoneOf
  , encode5D
  , distance5D
  , nearestNeighbors
  , constellationDetect
  , coherenceScore
  , holographicHash
  , mergeCoords
  ) where

import Data.Bits (xor)
import Data.List (sortOn)
import qualified Data.Vector as V

-- | 5D holographic coordinate (X, Y, Z, W, V).
data Coordinate5D = Coordinate5D
  { cx :: Double  -- ^ spatial X
  , cy :: Double  -- ^ spatial Y
  , cz :: Double  -- ^ spatial Z
  , cw :: Double  -- ^ temporal recency
  , cv :: Double  -- ^ valence / importance (0-1)
  } deriving (Show, Eq)

-- | Galactic zone based on V coordinate (valence/importance).
zoneOf :: Coordinate5D -> String
zoneOf c
  | cv c < 0.2  = "CORE"
  | cv c < 0.4  = "INNER_RING"
  | cv c < 0.6  = "MID_RING"
  | cv c < 0.8  = "OUTER_RING"
  | otherwise   = "FAR_EDGE"

-- | Deterministic pseudo-random sequence from a seed.
-- Simple linear congruential generator for reproducibility.
lcgSequence :: Int -> [Double]
lcgSequence seed = map normalise (iterate next seed)
  where
    next s = (1103515245 * s + 12345) `mod` 2147483647
    normalise s = fromIntegral s / 2147483647.0

-- | Encode a text string into a 5D holographic coordinate.
-- Uses the string's hash as a deterministic seed for reproducibility.
encode5D :: String -> Coordinate5D
encode5D text =
  let s = abs (hash text)
      vals = take 768 (lcgSequence s)
      vec = V.fromList vals
      norm = sqrt (V.sum (V.map (\v -> v * v) vec))
      nvec = if norm > 0 then V.map (/ norm) vec else vec
      x = V.sum (V.take 256 nvec) / 16.0
      y = V.sum (V.take 256 (V.drop 256 nvec)) / 16.0
      z = V.sum (V.drop 512 nvec) / 16.0
      w = clamp (fromIntegral (length text) / 1000.0)
      caps = fromIntegral (length (filter (`elem` ['A'..'Z']) text))
      punct = fromIntegral (length (filter (`elem` "!?.;:") text))
      v = clamp ((caps + 2 * punct) / max (fromIntegral (length text)) 1.0)
  in Coordinate5D (rnd x) (rnd y) (rnd z) (rnd w) (rnd v)
  where
    clamp v' = max 0.0 (min 1.0 v')
    rnd v' = fromIntegral (round (v' * 1e6)) / 1e6

-- | Compute string hash for seeding (simple djb2-like).
hash :: String -> Int
hash = foldl step 5381
  where step h c = ((h `shiftL` 5) + h) + fromEnum c
        shiftL x n = x * (2 ^ n)

-- | Euclidean distance in 5D holographic space.
-- V (valence) gets 2× weight because zone transitions matter more.
distance5D :: Coordinate5D -> Coordinate5D -> Double
distance5D a b =
  let dx = cx a - cx b
      dy = cy a - cy b
      dz = cz a - cz b
      dw = cw a - cw b
      dv = 2.0 * (cv a - cv b)
  in sqrt (dx*dx + dy*dy + dz*dz + dw*dw + dv*dv)

-- | Find k nearest neighbors to a query point.
-- Returns list of (index, distance) sorted by distance ascending.
nearestNeighbors :: Coordinate5D -> [Coordinate5D] -> Int -> [(Int, Double)]
nearestNeighbors query coords k =
  let indexed = zip [0..] (map (distance5D query) coords)
      sorted = take k (sortOn snd indexed)
  in sorted

-- | Detect constellations (clusters) in holographic space.
-- Single-linkage clustering with a distance threshold.
constellationDetect :: [Coordinate5D] -> Double -> Int -> [[Int]]
constellationDetect coords threshold minSize =
  let n = length coords
      parent = [0 .. n-1]
      -- Union-Find (simplified path compression)
      find p i = if p !! i == i then i else find p (p !! i)
      union p r i j =
        let ri = find p i
            rj = find p j
        in if ri == rj then (p, r)
           else if r !! ri < r !! rj
                then (take ri p ++ [rj] ++ drop (ri+1) p, r)
                else if r !! ri > r !! rj
                     then (take rj p ++ [ri] ++ drop (rj+1) p, r)
                     else (take rj p ++ [ri] ++ drop (rj+1) p,
                           take ri r ++ [r !! ri + 1] ++ drop (ri+1) r)
      -- Build adjacency and union
      pairs = [(i, j) | i <- [0..n-1], j <- [i+1..n-1]]
      (pFinal, _) = foldl (\(p, r) (i, j) ->
        if distance5D (coords !! i) (coords !! j) <= threshold
        then union p r i j
        else (p, r)) (parent, replicate n 0) pairs
      -- Collect components
      comps = foldl (\m i ->
        let root = find pFinal i
            existing = maybe [] id (lookup root m)
        in (root, i : existing) : filter ((/= root) . fst) m) [] [0..n-1]
      clusters = map snd comps
      valid = filter (\c -> length c >= minSize) clusters
  in sortOn (negate . length) valid

-- | Measure internal coherence of a memory cluster.
-- High coherence = tight cluster (low mean pairwise distance).
-- Returns 0.0-1.0.
coherenceScore :: [Coordinate5D] -> Double
coherenceScore coords =
  let n = length coords
  in if n < 2 then 1.0
     else let pairs = [(coords !! i, coords !! j) | i <- [0..n-1], j <- [i+1..n-1]]
              dists = map (uncurry distance5D) pairs
              meanDist = sum dists / fromIntegral (length dists)
          in max 0.0 (min 1.0 (1.0 - meanDist / 2.0))

-- | Locality-sensitive hash for 5D coordinates.
-- Memories with similar coordinates share hash prefixes.
holographicHash :: Coordinate5D -> Int -> String
holographicHash coord bins =
  let quantise v = min (bins - 1) (max 0 (floor ((v + 3.0) / 6.0 * fromIntegral bins)))
      bx = quantise (cx coord)
      by = quantise (cy coord)
      bz = quantise (cz coord)
      bw = quantise (cw coord)
      bv = quantise (cv coord)
      code = bx + by * bins + bz * bins^2 + bw * bins^3 + bv * bins^4
  in "H" ++ show code

-- | Merge multiple coordinates into a weighted centroid.
mergeCoords :: [Coordinate5D] -> [Double] -> Coordinate5D
mergeCoords coords weights =
  let n = length coords
  in if n == 0 then Coordinate5D 0 0 0 0 0
     else let w = if null weights then replicate n (1.0 / fromIntegral n)
                  else let total = sum weights in map (/ total) weights
              wxs = sum [cx (coords !! i) * (w !! i) | i <- [0..n-1]]
              wys = sum [cy (coords !! i) * (w !! i) | i <- [0..n-1]]
              wzs = sum [cz (coords !! i) * (w !! i) | i <- [0..n-1]]
              wws = sum [cw (coords !! i) * (w !! i) | i <- [0..n-1]]
              wvs = sum [cv (coords !! i) * (w !! i) | i <- [0..n-1]]
          in Coordinate5D (rnd wxs) (rnd wys) (rnd wzs) (rnd wws) (rnd wvs)
  where rnd v = fromIntegral (round (v * 1e6)) / 1e6
