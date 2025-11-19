{-# LANGUAGE RecordWildCards #-}

module Casting
    ( Context(..)
    , SystemState(..)
    , cast
    , castWith Entropy
    , interpret
    , changingLines
    , transform
    ) where

import IChing
import HexagramData
import qualified Data.Map.Strict as Map
import Data.List (foldl')
import Data.Text (Text)
import qualified Data.Text as T

-- | Context for casting
data Context = Context
    { keywords :: [Text]
    , sentiment :: Double  -- -1.0 (Yin) to 1.0 (Yang)
    , urgency :: Double    -- 0.0 (calm) to 1.0 (urgent)
    } deriving (Show, Eq)

-- | Current system state
data SystemState = SystemState
    { wuXingBalance :: WuXingState
    , memoryConfidence :: Double
    , recentPatterns :: [Text]
    } deriving (Show, Eq)

data WuXingState = WuXingState
    { wood :: Double
    , fire :: Double
    , earth :: Double
    , metal :: Double
    , water :: Double
    } deriving (Show, Eq)

-- | Pure functional hexagram casting
cast :: Context -> SystemState -> Hexagram
cast ctx state =
    let line1 = determineLine Foundation ctx state
        line2 = determineLine Resources ctx state
        line3 = determineLine Action ctx state
        line4 = determineLine Response ctx state
        line5 = determineLine Vision ctx state
        line6 = determineLine Transcendence ctx state
    in hexagram line1 line2 line3 line4 line5 line6

-- | Cast with added entropy (for mystery)
castWithEntropy :: Context -> SystemState -> Int -> Hexagram
castWithEntropy ctx state seed =
    let baseHex = cast ctx state
        entropy = fromIntegral (seed `mod` 10) / 100.0
    in if entropy < 0.1
       then baseHex  -- 90% deterministic
       else flip Line (seed `mod` 6) baseHex  -- 10% add mystery

-- | Determine single line based on position
determineLine :: Position -> Context -> SystemState -> Line
determineLine Foundation ctx state
    | earth (wuXingBalance state) > 0.5 = Yang
    | otherwise = Yin
determineLine Resources ctx state
    | memoryConfidence state > 0.7 = Yang
    | otherwise = Yin
determineLine Action ctx state
    | urgency ctx > 0.6 || hasKeyword "speed" ctx = Yang
    | otherwise = Yin
determineLine Response ctx state
    | sentiment ctx > 0.0 = Yang
    | otherwise = Yin
determineLine Vision ctx state
    | fire (wuXingBalance state) > 0.5 = Yang
    | otherwise = Yin
determineLine Transcendence ctx state
    | length (recentPatterns state) > 10 = Yang
    | otherwise = Yin

-- | Line positions
data Position = Foundation | Resources | Action | Response | Vision | Transcendence
    deriving (Show, Eq, Enum)

-- | Check if context has keyword
hasKeyword :: Text -> Context -> Bool
hasKeyword word ctx = word `elem` keywords ctx

-- | Interpret hexagram
interpret :: Hexagram -> Text
interpret hex =
    case getHexagramInfo (toNumber hex) of
        Just info -> judgment info
        Nothing -> "Unknown hexagram"

-- | Find changing lines (lines with strong energy)
changingLines :: Hexagram -> [Int]
changingLines hex =
    let yin Count = count Yin hex
        yangCount = 6 - yinCount
        imbalance = abs (yinCount - yangCount)
    in if imbalance >= 4
       then [1..6]  -- Strong imbalance = many changing lines
       else []      -- Balanced = stable

-- | Transform hexagram via changing lines
transform :: Hexagram -> Hexagram
transform hex =
    foldl' flipLineAt hex (changingLines hex)
  where
    flipLineAt h pos = modifyLine pos opposite h

-- | Count lines of a type
countLines :: Line -> Hexagram -> Int
countLines lineType hex = length $ filter (== lineType) $ linesOf hex

-- Helper to get lines from hexagram
linesOf :: Hexagram -> [Line]
linesOf (Hexagram l1 l2 l3 l4 l5 l6) = [l1, l2, l3, l4, l5, l6]

-- | Opposite line
opposite :: Line -> Line
opposite Yin = Yang
opposite Yang = Yin

-- | Modify line at position
modifyLine :: Int -> (Line -> Line) -> Hexagram -> Hexagram
modifyLine pos f (Hexagram l1 l2 l3 l4 l5 l6) = case pos of
    1 -> Hexagram (f l1) l2 l3 l4 l5 l6
    2 -> Hexagram l1 (f l2) l3 l4 l5 l6
    3 -> Hexagram l1 l2 (f l3) l4 l5 l6
    4 -> Hexagram l1 l2 l3 (f l4) l5 l6
    5 -> Hexagram l1 l2 l3 l4 (f l5) l6
    6 -> Hexagram l1 l2 l3 l4 l5 (f l6)
    _ -> Hexagram l1 l2 l3 l4 l5 l6  -- Invalid position

-- | Flip a line
flipLine :: Int -> Hexagram -> Hexagram
flipLine pos = modifyLine pos opposite
