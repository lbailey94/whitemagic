{-# LANGUAGE OverloadedStrings #-}

module HexagramData
    ( HexagramInfo(..)
    , allHexagramData
    , getHexagramInfo
    ) where

import qualified Data.Map.Strict as Map
import Data.Text (Text)

-- | Complete information for a hexagram
data HexagramInfo = HexagramInfo
    { number :: Int
    , chineseName :: Text
    , englishName :: Text
    , judgment :: Text
    , image :: Text
    , lines :: [Text]  -- Six line interpretations
    , attributes :: [Text]  -- Keywords/attributes
    } deriving (Show, Eq)

-- | All 64 hexagrams with complete data
allHexagramData :: Map.Map Int HexagramInfo
allHexagramData = Map.fromList
    [ (1, hexagram1)   -- The Creative
    , (2, hexagram2)   -- The Receptive
    , (48, hexagram48) -- The Well
    -- ... more will be added
    ]

hexagram1 :: HexagramInfo
hexagram1 = HexagramInfo
    { number = 1
    , chineseName = "乾 (Qián)"
    , englishName = "The Creative"
    , judgment = "The Creative works sublime success, furthering through perseverance."
    , image = "The movement of heaven is full of power. Thus the superior man makes himself strong and untiring."
    , lines = 
        [ "Hidden dragon. Do not act."
        , "Dragon appearing in the field. It furthers one to see the great man."
        , "All day long the superior man is creatively active. At nightfall his mind is still beset with cares. Danger. No blame."
        , "Wavering flight over the depths. No blame."
        , "Flying dragon in the heavens. It furthers one to see the great man."
        , "Arrogant dragon will have cause to repent."
        ]
    , attributes = ["Heaven", "Creative", "Strong", "Active", "Father", "Yang"]
    }

hexagram2 :: HexagramInfo
hexagram2 = HexagramInfo
    { number = 2
    , chineseName = "坤 (Kūn)"
    , englishName = "The Receptive"
    , judgment = "The Receptive brings about sublime success, furthering through the perseverance of a mare."
    , image = "The earth's condition is receptive devotion. Thus the superior man who has breadth of character carries the outer world."
    , lines =
        [ "When there is hoarfrost underfoot, solid ice is not far off."
        , "Straight, square, great. Without purpose, yet nothing remains unfurthered."
        , "Hidden lines. One is able to remain persevering. If by chance you are in the service of a king, seek not works, but bring to completion."
        , "A tied-up sack. No blame, no praise."
        , "A yellow lower garment brings supreme good fortune."
        , "Dragons fight in the meadow. Their blood is black and yellow."
        ]
    , attributes = ["Earth", "Receptive", "Yielding", "Passive", "Mother", "Yin"]
    }

hexagram48 :: HexagramInfo
hexagram48 = HexagramInfo
    { number = 48
    , chineseName = "井 (Jǐng)"
    , englishName = "The Well"
    , judgment = "The town may be changed, but the well cannot be changed. It neither decreases nor increases. They come and go and draw from the well."
    , image = "Water over wood: the image of THE WELL. Thus the superior man encourages the people at their work, and exhorts them to help one another."
    , lines =
        [ "One does not drink the mud of the well. No animals come to an old well."
        , "At the well hole one shoots fishes. The jug is broken and leaks."
        , "The well is cleaned, but no one drinks from it. This is my heart's sorrow, for one might draw from it."
        , "The well is being lined. No blame."
        , "In the well there is a clear, cold spring from which one can drink."
        , "One draws from the well without hindrance. It is dependable. Supreme good fortune."
        ]
    , attributes = ["Water", "Wood", "Resources", "Nourishment", "Consistency", "Depth"]
    }

-- | Get hexagram info by number
getHexagramInfo :: Int -> Maybe HexagramInfo
getHexagramInfo n = Map.lookup n allHexagramData
