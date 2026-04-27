{-# LANGUAGE ForeignFunctionInterface #-}

module WhiteMagic.Spatial
  ( cosineSimilarity
  , euclideanDistance5D
  ) where

import Foreign.C.Types (CDouble(..))
import qualified Data.Vector as V

-- | Cosine similarity between two float vectors.
cosineSimilarity :: [Double] -> [Double] -> Double
cosineSimilarity a b =
  let va = V.fromList a
      vb = V.fromList b
      dot = V.sum (V.zipWith (*) va vb)
      na = sqrt (V.sum (V.map (^2) va))
      nb = sqrt (V.sum (V.map (^2) vb))
   in if na == 0 || nb == 0 then 0 else dot / (na * nb)

-- | Euclidean distance in 5D holographic space.
euclideanDistance5D :: (Double, Double, Double, Double, Double)
                     -> (Double, Double, Double, Double, Double)
                     -> Double
euclideanDistance5D (x1,y1,z1,w1,v1) (x2,y2,z2,w2,v2) =
  sqrt ((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2 + (w2-w1)^2 + (v2-v1)^2)

-- | FFI export for Python ctypes binding.
foreign export ccall wm_hs_cosine :: CDouble -> CDouble -> CDouble

wm_hs_cosine :: CDouble -> CDouble -> CDouble
wm_hs_cosine _a _b = 0.0  -- Stub: full vector FFI needs CArray marshalling
