#!/usr/bin/env runhaskell
-- WhiteMagic Haskell JSON stdio bridge
-- Minimal standalone with custom JSON (no external deps)

import System.IO
import Data.List (intercalate)

data Coordinate5D = Coordinate5D
  { cx :: Double, cy :: Double, cz :: Double, cw :: Double, cv :: Double }

-- ---- Minimal JSON ----

data JVal = JStr String | JNum Double | JObj [(String, JVal)] | JArr [JVal] | JBool Bool | JNull

instance Show JVal where
  show (JStr s) = "\"" ++ escape s ++ "\""
  show (JNum n) = if n == fromIntegral (round n) then show (round n :: Int) else show n
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
jnum _ = 0.0

jarr :: JVal -> [JVal]
jarr (JArr a) = a
jarr _ = []

jobj :: JVal -> [(String, JVal)]
jobj (JObj o) = o
jobj _ = []

-- Very simple JSON parser for our limited use case
parseJSON :: String -> JVal
parseJSON s = fst (parseValue (trim s))
  where
    trim = reverse . dropWhile (== ' ') . reverse . dropWhile (== ' ')
    parseValue ('"':cs) = parseStr cs ""
    parseValue ('{':cs) = parseObj (trim cs) []
    parseValue ('[':cs) = parseArr (trim cs) []
    parseValue ('t':'r':'u':'e':cs) = (JBool True, cs)
    parseValue ('f':'a':'l':'s':'e':cs) = (JBool False, cs)
    parseValue ('n':'u':'l':'l':cs) = (JNull, cs)
    parseValue cs = parseNum cs ""

    parseStr ('"':cs) acc = (JStr (reverse acc), cs)
    parseStr ('\\':'"':cs) acc = parseStr cs ('"':acc)
    parseStr ('\\':'\\':cs) acc = parseStr cs ('\\':acc)
    parseStr ('\\':'n':cs) acc = parseStr cs ('\n':acc)
    parseStr (c:cs) acc = parseStr cs (c:acc)
    parseStr [] acc = (JStr (reverse acc), [])

    parseObj ('}':cs) acc = (JObj (reverse acc), cs)
    parseObj cs acc =
      let (JStr k, rest1) = parseValue (trim cs)
          rest2 = dropWhile (== ' ') (dropWhile (== ':') (dropWhile (== ' ') rest1))
          (v, rest3) = parseValue (trim rest2)
          rest4 = trim rest3
      in case rest4 of
           ',':rest5 -> parseObj (trim rest5) ((k, v):acc)
           '}':rest5 -> (JObj (reverse ((k, v):acc)), rest5)
           _ -> parseObj rest4 ((k, v):acc)

    parseArr (']':cs) acc = (JArr (reverse acc), cs)
    parseArr cs acc =
      let (v, rest1) = parseValue (trim cs)
          rest2 = trim rest1
      in case rest2 of
           ',':rest3 -> parseArr (trim rest3) (v:acc)
           ']':rest3 -> (JArr (reverse (v:acc)), rest3)
           _ -> parseArr rest2 (v:acc)

    parseNum cs acc =
      case cs of
        (c:rest) | c `elem` ('-':'.':'e':'E':'+':['0'..'9']) -> parseNum rest (c:acc)
        rest -> (JNum (read (reverse acc) :: Double), rest)

-- ---- Holographic Core ----

hash_djb2 :: String -> Int
hash_djb2 = foldl step 5381
  where step h c = ((h * 32) + h) + fromEnum c

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
  sqrt ((cx a - cx b)^2 + (cy a - cy b)^2 + (cz a - cz b)^2
        + (cw a - cw b)^2 + (2 * (cv a - cv b))^2)

zoneOf :: Coordinate5D -> String
zoneOf c
  | cv c < 0.2  = "CORE"
  | cv c < 0.4  = "INNER_RING"
  | cv c < 0.6  = "MID_RING"
  | cv c < 0.8  = "OUTER_RING"
  | otherwise   = "FAR_EDGE"

nearestNeighbors :: Coordinate5D -> [Coordinate5D] -> Int -> [(Int, Double)]
nearestNeighbors query pts k =
  let dists = zip [0..] (map (distance5D query) pts)
      sorted = insertSort (\(_, d1) (_, d2) -> compare d1 d2) dists
  in take k sorted

insertSort :: (a -> a -> Ordering) -> [a] -> [a]
insertSort cmp = foldr ins []
  where
    ins x [] = [x]
    ins x (y:ys) = case cmp x y of
                     LT -> x:y:ys
                     _  -> y:ins x ys

coordToJSON :: Coordinate5D -> JVal
coordToJSON c = JObj
  [ ("x", JNum (cx c)), ("y", JNum (cy c)), ("z", JNum (cz c))
  , ("w", JNum (cw c)), ("v", JNum (cv c)), ("zone", JStr (zoneOf c))
  ]

-- ---- Request Handler ----

handle :: [(String, JVal)] -> JVal
handle obj =
  let method = jstr (maybe (JStr "") id (jlookup "method" obj))
      p = jobj (maybe (JObj []) id (jlookup "params" obj))
      getStr k = jstr (maybe (JStr "") id (jlookup k p))
      getTexts k = map jstr (jarr (maybe (JArr []) id (jlookup k p)))
      getInt k d = round (jnum (maybe (JNum (fromIntegral d)) id (jlookup k p)))
  in case method of
    "ping" -> JObj [("status", JStr "ok"), ("backend", JStr "haskell")]
    "encode" ->
      let coord = encode5D (getStr "text")
      in JObj [("status", JStr "ok"), ("result", coordToJSON coord)]
    "nearest_neighbors" ->
      let query = encode5D (getStr "query")
          coords = map encode5D (getTexts "texts")
          k = getInt "k" 3
          results = nearestNeighbors query coords k
          resultsJSON = map (\(i, d) -> JObj [("index", JNum (fromIntegral i)), ("distance", JNum d)]) results
      in JObj [("status", JStr "ok"), ("results", JArr resultsJSON)]
    _ -> JObj [("status", JStr "error"), ("error", JStr ("Unknown method: " ++ method))]

mainLoop :: IO ()
mainLoop = do
  eof <- isEOF
  if eof then return () else do
    line <- getLine
    let req = parseJSON line
    let resp = handle (jobj req)
    putStrLn (show resp)
    hFlush stdout
    mainLoop

main :: IO ()
main = do
  hSetBuffering stdout LineBuffering
  hSetBuffering stdin LineBuffering
  mainLoop
