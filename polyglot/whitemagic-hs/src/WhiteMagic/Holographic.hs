module WhiteMagic.Holographic
  ( Coordinate5D(..)
  , zoneOf
  ) where

-- | 5D holographic coordinate.
data Coordinate5D = Coordinate5D
  { cx :: Double
  , cy :: Double
  , cz :: Double
  , cw :: Double
  , cv :: Double
  } deriving (Show, Eq)

-- | Galactic zone based on V coordinate (valence/importance).
zoneOf :: Coordinate5D -> String
zoneOf c
  | cv c < 0.2  = "CORE"
  | cv c < 0.4  = "INNER_RING"
  | cv c < 0.6  = "MID_RING"
  | cv c < 0.8  = "OUTER_RING"
  | otherwise   = "FAR_EDGE"
