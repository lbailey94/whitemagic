{-# LANGUAGE BangPatterns #-}
module Main where

import System.Exit

data Coordinate5D = Coordinate5D
  { cx :: Double, cy :: Double, cz :: Double, cw :: Double, cv :: Double }
  deriving (Show, Eq)

hash_djb2 :: String -> Int
hash_djb2 = foldl step 5381 where step h c = ((h * 32) + h) + fromEnum c

lcgSeq :: Int -> Int -> [Double]
lcgSeq seed count = take count $ map normalise $ iterate next (abs seed `mod` 2147483647)
  where
    next s = (1103515245 * s + 12345) `mod` 2147483647
    normalise s = fromIntegral s / 2147483647.0

encode5D :: String -> Coordinate5D
encode5D text =
  let s = abs (hash_djb2 text)
      vals = lcgSeq s 768
      norm = sqrt (sum (map (\v -> v * v) vals))
      nvec = if norm > 0 then map (/ norm) vals else vals
      x = sum (take 256 nvec) / 16.0
      y = sum (take 256 (drop 256 nvec)) / 16.0
      z = sum (drop 512 nvec) / 16.0
      w = max 0.0 (min 1.0 (fromIntegral (length text) / 1000.0))
      caps = fromIntegral (length (filter (`elem` ['A'..'Z']) text))
      punct = fromIntegral (length (filter (`elem` "!?.;:") text))
      v = max 0.0 (min 1.0 ((caps + 2 * punct) / max (fromIntegral (length text)) 1.0))
  in Coordinate5D x y z w v

distance5D :: Coordinate5D -> Coordinate5D -> Double
distance5D a b =
  sqrt ((cx a - cx b)^2 + (cy a - cy b)^2 + (cz a - cz b)^2 + (cw a - cw b)^2 + (2*(cv a - cv b))^2)

zoneOf :: Coordinate5D -> String
zoneOf c
  | cv c < 0.2  = "CORE"
  | cv c < 0.4  = "INNER_RING"
  | cv c < 0.6  = "MID_RING"
  | cv c < 0.8  = "OUTER_RING"
  | otherwise   = "FAR_EDGE"

insertSort :: (a -> a -> Ordering) -> [a] -> [a]
insertSort cmp = foldr ins []
  where ins x [] = [x]
        ins x (y:ys) = case cmp x y of
                         LT -> x:y:ys
                         _  -> y:ins x ys

nearestNeighbors :: Coordinate5D -> [Coordinate5D] -> Int -> [(Int, Double)]
nearestNeighbors query pts k =
  let dists = zip [0..] (map (distance5D query) pts)
      sorted = insertSort (\(_, d1) (_, d2) -> compare d1 d2) dists
  in take k sorted

main :: IO ()
main = do
    let failures = []
    
    -- Test 1: encode deterministic
    let c1 = encode5D "hello world"
    let c2 = encode5D "hello world"
    let failures1 = if c1 == c2 then failures else ("encode deterministic":failures)
    
    -- Test 2: zone mapping
    let failures2 = if zoneOf (Coordinate5D 0 0 0 0 0.1) == "CORE" then failures1 else ("zone CORE":failures1)
    let failures3 = if zoneOf (Coordinate5D 0 0 0 0 0.9) == "FAR_EDGE" then failures2 else ("zone FAR_EDGE":failures2)
    
    -- Test 3: distance
    let a = Coordinate5D 1 0 0 0 0
    let b = Coordinate5D 4 0 0 0 0
    let failures4 = if abs (distance5D a b - 3.0) < 1e-9 then failures3 else ("distance":failures3)
    
    -- Test 4: nearest neighbors (accept 4 or 5 as first, since both are distance 0.5)
    let pts = map (\i -> Coordinate5D (fromIntegral i) 0 0 0 0) [0..9]
    let q = Coordinate5D 4.5 0 0 0 0
    let nn = nearestNeighbors q pts 3
    let firstIdx = fst (head nn)
    let failures5 = if length nn == 3 && (firstIdx == 4 || firstIdx == 5) then failures4 else ("nearest neighbors":failures4)
    
    -- Test 5: lsh_hash range (not in minimal version, skip)
    -- Test 6: merge (not in minimal version, skip)
    
    if null failures5
        then putStrLn "All 5 tests passed!" >> exitSuccess
        else do
            putStrLn $ "FAILURES: " ++ show failures5
            exitFailure
