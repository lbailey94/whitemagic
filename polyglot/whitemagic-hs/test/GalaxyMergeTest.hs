module Main where

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import GalaxyMerge

-- Test helpers
mkMem :: String -> String -> Double -> String -> MemoryRecord
mkMem mid content imp ts = MemoryRecord
  { memId = MemoryID mid
  , memContent = content
  , memImportance = imp
  , memGalaxy = GalaxyID "test"
  , memTimestamp = ts
  }

assertEq :: (Eq a, Show a) => String -> a -> a -> IO ()
assertEq label actual expected =
  if actual == expected
    then putStrLn $ "  PASS: " ++ label
    else do
      putStrLn $ "  FAIL: " ++ label
      putStrLn $ "    expected: " ++ show expected
      putStrLn $ "    actual:   " ++ show actual

assertTrue :: String -> Bool -> IO ()
assertTrue label cond =
  if cond
    then putStrLn $ "  PASS: " ++ label
    else putStrLn $ "  FAIL: " ++ label

main :: IO ()
main = do
  putStrLn "=== GalaxyMerge Tests ==="

  putStrLn "Test: defaultSchema"
  assertEq "galaxy ID" (schemaGalaxyId (defaultSchema (GalaxyID "oracle"))) (GalaxyID "oracle")
  assertEq "4 types" (length (schemaAllowedTypes (defaultSchema (GalaxyID "test")))) 4
  assertEq "no capacity limit" (schemaMaxMemories (defaultSchema (GalaxyID "test"))) Nothing

  putStrLn "Test: schemaCompatible"
  assertEq "same galaxy compatible" (schemaCompatible (defaultSchema (GalaxyID "a")) (defaultSchema (GalaxyID "a"))) True
  assertEq "different galaxy compatible" (schemaCompatible (defaultSchema (GalaxyID "a")) (defaultSchema (GalaxyID "b"))) True

  let targetSchema = defaultSchema (GalaxyID "target")
      sourceSchema = defaultSchema (GalaxyID "source")
      targetMems = Map.fromList [(MemoryID "m1", mkMem "m1" "hello" 0.5 "2026-01-01")]

  putStrLn "Test: validateMerge no conflicts"
  let sourceMems1 = Map.fromList [(MemoryID "m2", mkMem "m2" "world" 0.6 "2026-01-02")]
      conflicts1 = validateMerge targetSchema targetMems sourceSchema sourceMems1
  assertEq "no conflicts" conflicts1 ([] :: [MergeConflict])

  putStrLn "Test: validateMerge duplicate"
  let sourceMems2 = Map.fromList [(MemoryID "m1", mkMem "m1" "world" 0.6 "2026-01-02")]
      conflicts2 = validateMerge targetSchema targetMems sourceSchema sourceMems2
  assertTrue "has conflicts" (not (null conflicts2))

  putStrLn "Test: merge source wins"
  let result1 = mergeGalaxies targetSchema targetMems sourceSchema sourceMems2 StrategySourceWins
  assertTrue "merge succeeds" (mergeSuccess result1)

  putStrLn "Test: merge target wins"
  let result2 = mergeGalaxies targetSchema targetMems sourceSchema sourceMems2 StrategyTargetWins
  assertTrue "merge succeeds" (mergeSuccess result2)

  putStrLn "Test: merge higher importance"
  let result3 = mergeGalaxies targetSchema targetMems sourceSchema sourceMems2 StrategyHigherImportance
  assertTrue "merge succeeds" (mergeSuccess result3)

  putStrLn "Test: merge new memories added"
  let sourceMems3 = Map.fromList
        [ (MemoryID "m1", mkMem "m1" "updated" 0.5 "2026-01-01")
        , (MemoryID "m2", mkMem "m2" "new" 0.7 "2026-01-02")
        , (MemoryID "m3", mkMem "m3" "newer" 0.8 "2026-01-03")
        ]
      result4 = mergeGalaxies targetSchema targetMems sourceSchema sourceMems3 StrategySourceWins
  assertEq "2 new added" (length (mergeAdded result4)) 2
  assertEq "total is 3" (mergeTotal result4) 3

  putStrLn "Test: merge identical duplicates skipped"
  let mem = mkMem "m1" "same" 0.5 "2026-01-01"
      targetMems5 = Map.fromList [(MemoryID "m1", mem)]
      sourceMems5 = Map.fromList [(MemoryID "m1", mem)]
      result5 = mergeGalaxies targetSchema targetMems5 sourceSchema sourceMems5 StrategySourceWins
  assertEq "1 skipped" (length (mergeSkipped result5)) 1
  assertEq "0 added" (length (mergeAdded result5)) 0

  putStrLn "Test: merge empty source"
  let result6 = mergeGalaxies targetSchema targetMems sourceSchema Map.empty StrategySourceWins
  assertTrue "merge succeeds" (mergeSuccess result6)
  assertEq "0 added" (length (mergeAdded result6)) 0

  putStrLn "Test: merge empty target"
  let result7 = mergeGalaxies targetSchema Map.empty sourceSchema sourceMems3 StrategySourceWins
  assertTrue "merge succeeds" (mergeSuccess result7)
  assertEq "3 added" (length (mergeAdded result7)) 3

  putStrLn "=== All tests complete ==="
