{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE DeriveAnyClass #-}

{-|
Module      : IChing
Description : I Ching 64-hexagram state machine for memory system states
Copyright   : (c) WhiteMagic Contributors, 2025
License     : MIT
Maintainer  : whitemagic@example.com

The I Ching provides a complete state space (2^6 = 64 hexagrams) for
modeling system states. Each hexagram represents a unique configuration
of six binary lines (yin/yang), mapping perfectly to system state dimensions.

Philosophy: Ancient wisdom meets modern type theory. Pure functional state
transitions with compile-time correctness guarantees.
-}

module IChing
    ( -- * Core Types
      Line(..)
    , Trigram(..)
    , Hexagram(..)
    , HexagramName(..)
    
      -- * State Transitions
    , transition
    , oppositeHexagram
    , complementaryHexagram
    
      -- * Hexagram Construction
    , hexagram
    , fromNumber
    , toNumber
    , toKingWenNumber
    , fromKingWenNumber
    
      -- * Queries
    , isBalanced
    , yinYangRatio
    , dominantForce
    
      -- * All Hexagrams
    , allHexagrams
    ) where

import GHC.Generics (Generic)
import Data.List (foldl')
import Data.Array (Array, listArray, accumArray, (!))

-- | Yin (broken) or Yang (solid) line
data Line = Yin | Yang
    deriving (Eq, Show, Generic, Enum, Bounded)

-- | Three lines forming a trigram (8 total combinations)
data Trigram = Trigram Line Line Line
    deriving (Eq, Show, Generic)

-- | Six lines forming a hexagram (64 total combinations)
-- Upper trigram (Heaven) and Lower trigram (Earth)
data Hexagram = Hexagram 
    { upper :: Trigram  -- Heaven (top 3 lines)
    , lower :: Trigram  -- Earth (bottom 3 lines)
    } deriving (Eq, Show, Generic)

-- | Traditional I Ching hexagram names (King Wen sequence)
data HexagramName
    = TheCreative          -- 1. ䷀ Qián (乾)
    | TheReceptive         -- 2. ䷁ Kūn (坤)  
    | DifficultyAtBeginning -- 3. ䷂ Zhūn (屯)
    | YouthfulFolly        -- 4. ䷃ Méng (蒙)
    | Waiting              -- 5. ䷄ Xū (需)
    | Conflict             -- 6. ䷅ Sòng (訟)
    -- ... (all 64 hexagrams would be here in full implementation)
    | Custom Int           -- Placeholder for remaining hexagrams
    deriving (Eq, Show, Generic)

-- | Convert line to binary (0 or 1)
lineToBit :: Line -> Int
lineToBit Yin = 0
lineToBit Yang = 1

-- | Convert binary to line
bitToLine :: Int -> Line
bitToLine 0 = Yin
bitToLine _ = Yang

-- | Opposite line (yin ↔ yang)
oppositeLine :: Line -> Line
oppositeLine Yin = Yang
oppositeLine Yang = Yin

-- | Create hexagram from six lines (bottom to top)
hexagram :: Line -> Line -> Line -> Line -> Line -> Line -> Hexagram
hexagram l1 l2 l3 l4 l5 l6 = Hexagram
    { upper = Trigram l4 l5 l6  -- Top 3 lines
    , lower = Trigram l1 l2 l3  -- Bottom 3 lines
    }

-- | Convert hexagram to binary sequence number (1-64, Fu Xi order).
-- This is the raw binary value + 1, NOT the King Wen number.
toNumber :: Hexagram -> Int
toNumber (Hexagram (Trigram u1 u2 u3) (Trigram l1 l2 l3)) =
    let bits = map lineToBit [l1, l2, l3, u1, u2, u3]
        binary = foldl' (\acc b -> acc * 2 + b) 0 bits
    in binary + 1  -- binary 0-63 → 1-64

-- | Convert number (1-64, binary/Fu Xi sequence) to hexagram
fromNumber :: Int -> Maybe Hexagram
fromNumber n 
    | n < 1 || n > 64 = Nothing
    | otherwise = Just $ numToHex (n - 1)
  where
    numToHex :: Int -> Hexagram
    numToHex num =
        case map bitToLine $ reverse $ take 6 $ toBinary num ++ repeat 0 of
            [l1, l2, l3, u1, u2, u3] -> hexagram l1 l2 l3 u1 u2 u3
            _                        -> hexagram Yin Yin Yin Yin Yin Yin  -- unreachable
    
    toBinary :: Int -> [Int]
    toBinary 0 = []
    toBinary n' = toBinary (n' `div` 2) ++ [n' `mod` 2]

-- ---------------------------------------------------------------------------
-- King Wen sequence conversion
-- ---------------------------------------------------------------------------

-- | King Wen table: maps binary index (0-63) → King Wen number (1-64).
-- Binary: bit 0 = bottom line, bit 5 = top line. 1=Yang, 0=Yin.
-- Cross-referenced with Wikibooks "I Ching/The 64 Hexagrams".
kingWenTable :: Array Int Int
kingWenTable = listArray (0, 63)
    [  2, 24,  7, 19, 15, 36, 46, 11
    , 16, 51, 40, 54, 62, 55, 32, 34
    ,  8,  3, 29, 60, 39, 63, 48,  5
    , 45, 17, 47, 58, 31, 49, 28, 43
    , 23, 27,  4, 41, 52, 22, 18, 26
    , 35, 21, 64, 38, 56, 30, 50, 14
    , 20, 42, 59, 61, 53, 37, 57,  9
    , 12, 25,  6, 10, 33, 13, 44,  1
    ]

-- | Inverse King Wen table: King Wen number (1-64) → binary index (0-63).
kingWenInverse :: Array Int Int
kingWenInverse = accumArray (\_ b -> b) 0 (1, 64)
    [ (kingWenTable ! i, i) | i <- [0..63] ]

-- | Convert hexagram to King Wen number (1-64).
-- The KING_WEN table uses bit 0 = bottom line (l1), but toNumber uses l1 as MSB.
-- We reverse the bit order to get the correct table index.
toKingWenNumber :: Hexagram -> Int
toKingWenNumber (Hexagram (Trigram u1 u2 u3) (Trigram l1 l2 l3)) =
    let bits = map lineToBit [l1, l2, l3, u1, u2, u3]
        -- Reverse so l1 becomes bit 0 (LSB)
        binary = foldl' (\acc b -> acc * 2 + b) 0 (reverse bits)
    in kingWenTable ! binary

-- | Convert King Wen number (1-64) to hexagram.
fromKingWenNumber :: Int -> Maybe Hexagram
fromKingWenNumber n
    | n < 1 || n > 64 = Nothing
    | otherwise =
        let binary = kingWenInverse ! n
            -- Extract bits LSB-first (bit 0 = l1 = bottom line)
            toBits 0 = []
            toBits x = (x `mod` 2) : toBits (x `div` 2)
            bits6 = take 6 (toBits binary ++ repeat 0)
            [l1, l2, l3, u1, u2, u3] = map bitToLine bits6
        in Just $ hexagram l1 l2 l3 u1 u2 u3

-- | State transition: change one or more lines
-- This models how system state evolves
transition :: [Int]  -- ^ Line positions to change (1-6, bottom to top)
           -> Hexagram
           -> Hexagram
transition positions (Hexagram (Trigram u1 u2 u3) (Trigram l1 l2 l3)) =
    let allLines = [l1, l2, l3, u1, u2, u3]
        changed = zipWith (\i line -> if i `elem` positions
                                       then oppositeLine line
                                       else line) [1..6] allLines
    in case changed of
        [nl1, nl2, nl3, nu1, nu2, nu3] -> hexagram nl1 nl2 nl3 nu1 nu2 nu3
        _                              -> hexagram l1 l2 l3 u1 u2 u3  -- unreachable

-- | Opposite hexagram (all lines reversed)
oppositeHexagram :: Hexagram -> Hexagram
oppositeHexagram = transition [1,2,3,4,5,6]

-- | Complementary hexagram (rotated 180°, 綜卦 zōng guà)
-- In King Wen sequence, 28 of the 32 pairs are inversions of each other.
-- A true 180° rotation reverses the order of all 6 lines:
--   line 1 (bottom) ↔ line 6 (top), line 2 ↔ line 5, line 3 ↔ line 4
complementaryHexagram :: Hexagram -> Hexagram
complementaryHexagram (Hexagram (Trigram u1 u2 u3) (Trigram l1 l2 l3)) =
    -- After rotation: old top line (u3) becomes new bottom line
    -- New lower = [u3, u2, u1], new upper = [l3, l2, l1]
    hexagram u3 u2 u1 l3 l2 l1

-- | Check if hexagram is balanced (3 yin, 3 yang)
isBalanced :: Hexagram -> Bool
isBalanced hex = yinYangRatio hex == (3, 3)

-- | Count yin and yang lines
yinYangRatio :: Hexagram -> (Int, Int)
yinYangRatio (Hexagram (Trigram u1 u2 u3) (Trigram l1 l2 l3)) =
    let allLines = [l1, l2, l3, u1, u2, u3]
        yinCount = length $ filter (== Yin) allLines
        yangCount = 6 - yinCount
    in (yinCount, yangCount)

-- | Determine dominant force
data Force = YinDominant | YangDominant | Balanced
    deriving (Eq, Show)

dominantForce :: Hexagram -> Force
dominantForce hex =
    case yinYangRatio hex of
        (y, ya) | y > ya    -> YinDominant
                | ya > y    -> YangDominant
                | otherwise -> Balanced

-- | All 64 hexagrams
allHexagrams :: [Hexagram]
allHexagrams = [hexagram l1 l2 l3 l4 l5 l6 
               | l1 <- [Yin, Yang]
               , l2 <- [Yin, Yang]
               , l3 <- [Yin, Yang]
               , l4 <- [Yin, Yang]
               , l5 <- [Yin, Yang]
               , l6 <- [Yin, Yang]
               ]

