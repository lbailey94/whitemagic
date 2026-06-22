module Main where

import WhiteMagic.Holographic
import System.CPUTime

sec :: Integer -> Integer -> Double
sec t0 t1 = fromIntegral (t1 - t0) / (10^12)

main :: IO ()
main = do
    putStrLn "=== Haskell Holographic Memory Benchmark ==="

    let n = 1000
    t0 <- getCPUTime
    let texts = ["memory " ++ show i ++ " with some text content" | i <- [1..n]]
    let coords = map encode5D texts
    t1 <- getCPUTime
    let encSec = sec t0 t1
    putStrLn $ "Encode " ++ show n ++ " texts: " ++ show encSec ++ " s (" ++ show (fromIntegral n / encSec) ++ " texts/sec)"

    let query = encode5D "search query"
    t0 <- getCPUTime
    let _ = take 5 (nearestNeighbors query coords 5)
    t1 <- getCPUTime
    putStrLn $ "NN search (1x): " ++ show (sec t0 t1) ++ " s"

    t0 <- getCPUTime
    let clusters = constellationDetect coords 0.8 3
    t1 <- getCPUTime
    putStrLn $ "Constellation detect: " ++ show (sec t0 t1) ++ " s (" ++ show (length clusters) ++ " clusters)"

    t0 <- getCPUTime
    let _ = map (\c -> (holographicHash c 8, zoneOf c)) coords
    t1 <- getCPUTime
    putStrLn $ "Hash+Zone (" ++ show n ++ " items): " ++ show (sec t0 t1) ++ " s"

    t0 <- getCPUTime
    let _ = map (\i -> mergeCoords [coords !! i, coords !! (i + 1)] [0.5, 0.5]) [0..99]
    t1 <- getCPUTime
    putStrLn $ "Merge (100x): " ++ show (sec t0 t1) ++ " s"

    putStrLn "\n=== DONE ==="
