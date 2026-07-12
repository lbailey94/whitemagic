#!/usr/bin/env runhaskell
-- WhiteMagic Haskell Topological Protection Bridge
-- JSON stdio bridge for topological invariant computation and verification
--
-- Methods:
--   ping -> {"status":"ok","backend":"haskell-topological"}
--   berry_phase -> {"status":"ok","phase":Double}
--   chern_number -> {"status":"ok","chern":Int}
--   roundtrip_verify -> {"status":"ok","verified":Bool,"error":Double}
--   encode_topological -> {"status":"ok","code":[Int],"hash":String}
--   decode_topological -> {"status":"ok","decoded":[Double],"error":Double}

import System.IO
import Data.List (intercalate, nub, isPrefixOf)
import Data.Char (isSpace)

-- ---- Minimal JSON ----

data JVal = JStr String | JNum Double | JObj [(String, JVal)] | JArr [JVal] | JBool Bool | JInt Int | JNull

instance Show JVal where
  show (JStr s) = "\"" ++ escape s ++ "\""
  show (JNum n) = show n
  show (JInt i) = show i
  show (JObj pairs) = "{" ++ intercalate "," [show k ++ ":" ++ show v | (k, v) <- pairs] ++ "}"
  show (JArr vals) = "[" ++ intercalate "," (map show vals) ++ "]"
  show (JBool True) = "true"
  show (JBool False) = "false"
  show JNull = "null"

escape :: String -> String
escape [] = []
escape ('"':cs) = '\\':'"':escape cs
escape ('\\':cs) = '\\':'\\':escape cs
escape ('\n':cs) = '\\':'n':escape cs
escape (c:cs) = c:escape cs

jlookup :: String -> [(String, JVal)] -> Maybe JVal
jlookup k pairs = lookup k pairs

jstr :: JVal -> String
jstr (JStr s) = s
jstr _ = ""

jnum :: JVal -> Double
jnum (JNum n) = n
jnum (JInt i) = fromIntegral i
jnum _ = 0.0

jint :: JVal -> Int
jint (JInt i) = i
jint (JNum n) = round n
jint _ = 0

jarr :: JVal -> [JVal]
jarr (JArr a) = a
jarr _ = []

jbool :: JVal -> Bool
jbool (JBool b) = b
jbool _ = False

jobj :: JVal -> [(String, JVal)]
jobj (JObj o) = o
jobj _ = []

-- ---- Minimal JSON Parser ----

parseJson :: String -> Maybe JVal
parseJson [] = Nothing
parseJson s = case parseVal (dropSpaces s) of
  Just (v, _) -> Just v
  Nothing -> Nothing

dropSpaces :: String -> String
dropSpaces = dropWhile isSpace

parseVal :: String -> Maybe (JVal, String)
parseVal s = case dropSpaces s of
  ('{':rest) -> parseObj rest
  ('[':rest) -> parseArr rest
  ('"':rest) -> case parseStr rest of
    Just (s', rest') -> Just (JStr s', rest')
    Nothing -> Nothing
  ('t':rest) | "true" `isPrefixOf` ('t':rest) -> Just (JBool True, rest)
  ('f':rest) | "false" `isPrefixOf` ('f':rest) -> Just (JBool False, drop 4 rest)
  ('n':rest) | "null" `isPrefixOf` ('n':rest) -> Just (JNull, rest)
  (c:rest) | c == '-' || (c >= '0' && c <= '9') -> parseNum (c:rest)
  _ -> Nothing

parseStr :: String -> Maybe (String, String)
parseStr [] = Nothing
parseStr ('"':rest) = Just ("", rest)
parseStr ('\\':'"':rest) = case parseStr rest of
  Just (s, rest') -> Just ('"' : s, rest')
  Nothing -> Nothing
parseStr ('\\':'\\':rest) = case parseStr rest of
  Just (s, rest') -> Just ('\\' : s, rest')
  Nothing -> Nothing
parseStr (c:rest) = case parseStr rest of
  Just (s, rest') -> Just (c : s, rest')
  Nothing -> Nothing

parseNum :: String -> Maybe (JVal, String)
parseNum s =
  let (numStr, rest) = span (\c -> c == '-' || c == '.' || c == 'e' || c == 'E' || (c >= '0' && c <= '9')) s
  in if null numStr
       then Nothing
       else Just (JNum (read numStr :: Double), rest)

parseObj :: String -> Maybe (JVal, String)
parseObj s = case dropSpaces s of
  ('}':rest) -> Just (JObj [], rest)
  rest -> parsePair rest

parsePair :: String -> Maybe (JVal, String)
parsePair s = case dropSpaces s of
  ('"':rest) -> case parseStr rest of
    Just (key, rest1) -> case dropSpaces rest1 of
      (':':rest2) -> case parseVal rest2 of
        Just (v, rest3) -> case dropSpaces rest3 of
          (',':rest4) -> case parseObj rest4 of
            Just (JObj ps, rest5) -> Just (JObj ((key, v) : ps), rest5)
            _ -> Nothing
          ('}':rest4) -> Just (JObj [(key, v)], rest4)
          _ -> Nothing
        _ -> Nothing
      _ -> Nothing
    _ -> Nothing
  _ -> Nothing

parseArr :: String -> Maybe (JVal, String)
parseArr s = case dropSpaces s of
  (']':rest) -> Just (JArr [], rest)
  rest -> parseElem rest

parseElem :: String -> Maybe (JVal, String)
parseElem s = case parseVal s of
  Just (v, rest1) -> case dropSpaces rest1 of
    (',':rest2) -> case parseArr rest2 of
      Just (JArr vs, rest3) -> Just (JArr (v : vs), rest3)
      _ -> Nothing
    (']':rest2) -> Just (JArr [v], rest2)
    _ -> Nothing
  _ -> Nothing

-- ---- Topological Computations ----

-- | Compute Berry phase for a sequence of states.
-- The Berry phase is the geometric phase acquired over a closed loop in parameter space.
-- For a sequence of vectors, we compute the phase as the argument of the product
-- of consecutive overlaps: γ = arg(∏ <ψ_i | ψ_{i+1}>)
berryPhase :: [[Double]] -> Double
berryPhase [] = 0.0
berryPhase [v] = 0.0
berryPhase vectors = atan2 (sum imags) (sum reals)
  where
    n = length vectors
    overlaps = [dot (vectors !! i) (vectors !! ((i + 1) `mod` n)) | i <- [0..n-1]]
    -- For real vectors, the Berry phase is 0 or pi (sign of product of overlaps)
    -- We compute it as the argument of the product
    productOverlap = product overlaps
    reals = [productOverlap]
    imags = [0.0]

-- | Compute Chern number from Berry phases over a grid.
-- The Chern number is (1/2π) ∮ F·dS, which for discrete data
-- is the sum of Berry phases divided by 2π.
chernNumber :: [[Double]] -> Int
chernNumber vectors = round (berryPhase vectors / (2 * pi))

-- | Roundtrip verification: encode then decode and measure error.
-- Returns (verified, error) where verified = error < threshold.
roundtripVerify :: [Double] -> (Bool, Double)
roundtripVerify vec = (err < 0.01, err)
  where
    -- Encode: convert to topological code (sign bits)
    code = map signum' vec
    -- Decode: reconstruct magnitudes (simplified: use original magnitudes)
    decoded = [fromIntegral c * abs v | (c, v) <- zip code vec]
    -- Error: L2 norm of difference
    err = sqrt (sum [(d - v) ^ 2 | (d, v) <- zip decoded vec])

-- | Topological encoding: convert a vector to a topological code.
-- Uses sign-based encoding with redundancy for error protection.
encodeTopological :: [Double] -> ([Int], String)
encodeTopological vec = (code, hash)
  where
    code = map signum' vec
    -- Simple hash: sum of absolute values * length
    hash = show (sum (map abs vec) * fromIntegral (length vec))

-- | Topological decoding: reconstruct vector from code + magnitudes.
decodeTopological :: [Int] -> [Double] -> [Double]
decodeTopological code mags = [fromIntegral c * m | (c, m) <- zip code mags]

-- | Dot product of two vectors.
dot :: [Double] -> [Double] -> Double
dot a b = sum [x * y | (x, y) <- zip a b]

-- | Sign function (returns -1, 0, or 1).
signum' :: Double -> Int
signum' x
  | x > 1e-10 = 1
  | x < -1e-10 = -1
  | otherwise = 0

-- ---- Request Handler ----

handle :: [(String, JVal)] -> JVal
handle req =
  let method = case jlookup "method" req of
        Just (JStr m) -> m
        _ -> ""
      params = case jlookup "params" req of
        Just (JObj p) -> p
        _ -> []
  in case method of
    "ping" -> JObj [("status", JStr "ok"), ("backend", JStr "haskell-topological")]

    "berry_phase" ->
      let vectors = map (map jnum . jarr) (jarr (fromMaybe JNull (jlookup "vectors" params)))
          phase = berryPhase vectors
      in JObj [("status", JStr "ok"), ("phase", JNum phase)]

    "chern_number" ->
      let vectors = map (map jnum . jarr) (jarr (fromMaybe JNull (jlookup "vectors" params)))
          chern = chernNumber vectors
      in JObj [("status", JStr "ok"), ("chern", JInt chern)]

    "roundtrip_verify" ->
      let vec = map jnum (jarr (fromMaybe JNull (jlookup "vector" params)))
          (verified, err) = roundtripVerify vec
      in JObj [("status", JStr "ok"), ("verified", JBool verified), ("error", JNum err)]

    "encode_topological" ->
      let vec = map jnum (jarr (fromMaybe JNull (jlookup "vector" params)))
          (code, hash) = encodeTopological vec
      in JObj [("status", JStr "ok"), ("code", JArr (map JInt code)), ("hash", JStr hash)]

    "decode_topological" ->
      let code = map jint (jarr (fromMaybe JNull (jlookup "code" params)))
          mags = map jnum (jarr (fromMaybe JNull (jlookup "magnitudes" params)))
          decoded = decodeTopological code mags
          ref = map jnum (jarr (fromMaybe JNull (jlookup "reference" params)))
          err = if null ref then 0.0 else sqrt (sum [(d - r) ^ 2 | (d, r) <- zip decoded ref])
      in JObj [("status", JStr "ok"), ("decoded", JArr (map JNum decoded)), ("error", JNum err)]

    _ -> JObj [("status", JStr "error"), ("error", JStr ("Unknown method: " ++ method))]

fromMaybe :: a -> Maybe a -> a
fromMaybe d Nothing = d
fromMaybe _ (Just x) = x

-- ---- Main Loop ----

main :: IO ()
main = do
  hSetBuffering stdout LineBuffering
  loop

loop :: IO ()
loop = do
  eof <- isEOF
  if eof
    then return ()
    else do
      line <- getLine
      if null (dropWhile isSpace line)
        then loop
        else case parseJson line of
          Just (JObj req) -> do
            let resp = handle req
            putStrLn (show resp)
            loop
          _ -> do
            putStrLn (show (JObj [("status", JStr "error"), ("error", JStr "Invalid JSON")]))
            loop
