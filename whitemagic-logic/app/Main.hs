module Main (main) where

import IChing
import Transform
import Query

main :: IO ()
main = do
    putStrLn "WhiteMagic Haskell Logic Layer"
    putStrLn "=============================="
    putStrLn ""
    putStrLn $ "Total hexagrams: " ++ show (length allHexagrams)
    putStrLn $ "The Creative (all Yang): " ++ show (toNumber theCreative)
    putStrLn $ "The Receptive (all Yin): " ++ show (toNumber theReceptive)
    putStrLn ""
    putStrLn "Type-safe memory transformations ready!"
    putStrLn "Query DSL ready!"
    putStrLn "FFI bindings ready for Python integration!"

theCreative :: Hexagram
theCreative = hexagram Yang Yang Yang Yang Yang Yang

theReceptive :: Hexagram
theReceptive = hexagram Yin Yin Yin Yin Yin Yin
