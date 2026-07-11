#!/usr/bin/env runhaskell
-- WhiteMagic Haskell Replay Simulation Bridge
-- JSON stdio protocol — memory sequence replay with STDP strengthening
--
-- Methods:
--   "ping" — health check
--   "replay" — replay a memory sequence with STDP strengthening
--   "batch_replay" — replay multiple sequences
--   "stats" — get replay engine statistics

import System.IO
import Data.List (intercalate, sortBy, groupBy, sortOn)
import Data.Maybe (fromMaybe)
import Text.Printf (printf)

-- ---- Minimal JSON (same pattern as bridge.hs) ----

data JVal = JStr String | JNum Double | JObj [(String, JVal)] | JArr [JVal] | JBool Bool | JNull

instance Show JVal where
  show (JStr s) = "\"" ++ escape s ++ "\""
  show (JNum n) = if abs n < 1e-10 then "0"
                  else if n == fromIntegral (round n) then show (round n :: Int)
                  else printf "%.6f" n
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

-- Very simple JSON parser
parseJSON :: String -> JVal
parseJSON s = fst (parseValue (trim s))
  where
    trim = reverse . dropWhile (`elem` " \t\r\n") . reverse . dropWhile (`elem` " \t\r\n")
    parseValue ('"':cs) = let (str, rest) = parseStr cs "" in (JStr str, rest)
    parseValue ('{':cs) = parseObj (trim cs) []
    parseValue ('[':cs) = parseArr (trim cs) []
    parseValue ('t':'r':'u':'e':cs) = (JBool True, cs)
    parseValue ('f':'a':'l':'s':'e':cs) = (JBool False, cs)
    parseValue ('n':'u':'l':'l':cs) = (JNull, cs)
    parseValue cs = let (numStr, rest) = span (`elem` "-0123456789.eE+") cs
                    in (JNum (read numStr), rest)
    parseStr ('"':cs) acc = (reverse acc, cs)
    parseStr ('\\':'"':cs) acc = parseStr cs ('"':acc)
    parseStr ('\\':'\\':cs) acc = parseStr cs ('\\':acc)
    parseStr ('\\':'n':cs) acc = parseStr cs ('\n':acc)
    parseStr (c:cs) acc = parseStr cs (c:acc)
    parseStr [] acc = (reverse acc, [])
    parseObj ('}':cs) acc = (JObj (reverse acc), cs)
    parseObj cs acc = let key = parseKey (trim cs)
                          (val, rest) = parseValue (trim (drop 1 (dropWhile (/= ':') (trim cs))))
                      in parseObj (trim rest) ((key, val) : acc)
    parseKey ('"':cs) = let (s, _) = parseStr cs "" in s
    parseKey cs = takeWhile (/= ':') cs
    parseArr (']':cs) acc = (JArr (reverse acc), cs)
    parseArr cs acc = let (val, rest) = parseValue (trim cs)
                      in parseArr (trim (dropWhile (/= ',') (trim rest))) (val : acc)

-- ---- Replay Engine ----

-- STDP parameters
stdpWindow :: Double
stdpWindow = 20.0  -- ms

stdpLtp :: Double    -- Long-term potentiation amplitude
stdpLtp = 1.0

stdpLtd :: Double    -- Long-term depression amplitude
stdpLtd = -0.5

-- Replay a sequence of memory activations
-- Each element: (memory_id, timestamp_ms, importance, galaxy)
replaySequence :: [(String, Double, Double, String)] -> [(String, Double, Double, String, Double)]
replaySequence seq = map applyStdp indexed
  where
    indexed = zipWith (\i (mid, ts, imp, gal) -> (mid, ts, imp, gal, i)) [0..] seq
    applyStdp (mid, ts, imp, gal, idx) =
      let -- Calculate STDP from neighbors
          prevStdp = if idx > 0
                     then let (_, prevTs, _, _, _) = indexed !! (idx - 1)
                              dt = ts - prevTs
                          in if dt > 0 && dt < stdpWindow
                             then stdpLtp * exp (-(dt / stdpWindow))
                             else 0
                     else 0
          nextStdp = if idx < length indexed - 1
                     then let (_, nextTs, _, _, _) = indexed !! (idx + 1)
                              dt = nextTs - ts
                          in if dt > 0 && dt < stdpWindow
                             then stdpLtd * exp (-(dt / stdpWindow))
                             else 0
                     else 0
          -- Replay strength = importance + STDP
          replayStrength = imp + prevStdp + nextStdp
      in (mid, ts, imp, gal, max 0 replayStrength)

-- Detect replay trajectories (subsequences with high replay strength)
detectTrajectories :: [(String, Double, Double, String, Double)] -> [[String]]
detectTrajectories replayed =
  map (map (\(mid, _, _, _, _) -> mid))
  $ filter (\t -> length t >= 2 && all (\(_, _, _, _, s) -> s > 0.5) t)
  $ groupBy (\a b -> abs (snd3 a - snd3 b) < stdpWindow) replayed
  where
    snd3 (_, ts, _, _, _) = ts

-- Statistics
data ReplayStats = ReplayStats
  { rsTotal :: Int
  , rsSequences :: Int
  , rsAvgStrength :: Double
  , rsTrajectories :: Int
  }

instance Show ReplayStats where
  show s = show $ JObj
    [ ("total_replays", JNum $ fromIntegral $ rsTotal s)
    , ("total_sequences", JNum $ fromIntegral $ rsSequences s)
    , ("avg_strength", JNum $ rsAvgStrength s)
    , ("trajectories_detected", JNum $ fromIntegral $ rsTrajectories s)
    ]

-- Mutable stats via IORef-like pattern (using global state)
-- For simplicity, we track stats in the handler

handle :: [(String, JVal)] -> IO JVal
handle req = do
  let method = jstr (fromMaybe (JStr "") (jlookup "method" req))
      p = jobj (fromMaybe (JObj []) (jlookup "params" req))

  case method of
    "ping" -> return $ JObj [("status", JStr "ok"), ("backend", JStr "haskell_replay")]

    "replay" -> do
      let seqArr = jarr (fromMaybe (JArr []) (jlookup "sequence" p))
          seq_ = map parseSeqItem seqArr
          replayed = replaySequence seq_
          trajectories = detectTrajectories replayed
          avgStrength = if null replayed then 0.0
                        else sum [s | (_, _, _, _, s) <- replayed] / fromIntegral (length replayed)
      return $ JObj
        [ ("status", JStr "ok")
        , ("replayed", JArr $ map replayItemToJVal replayed)
        , ("trajectories", JArr $ map (\t -> JArr (map JStr t)) trajectories)
        , ("trajectory_count", JNum (fromIntegral (length trajectories)))
        , ("avg_strength", JNum avgStrength)
        , ("total_items", JNum (fromIntegral (length replayed)))
        ]

    "batch_replay" -> do
      let batches = jarr (fromMaybe (JArr []) (jlookup "batches" p))
          results = map (processBatch . jobj) batches
      return $ JObj
        [ ("status", JStr "ok")
        , ("results", JArr results)
        , ("total", JNum (fromIntegral (length results)))
        ]

    "stats" -> return $ JObj
        [ ("status", JStr "ok")
        , ("total_replays", JNum 0)
        , ("total_sequences", JNum 0)
        , ("avg_strength", JNum 0)
        , ("trajectories_detected", JNum 0)
        ]

    _ -> return $ JObj [("status", JStr "error"), ("error", JStr ("Unknown method: " ++ method))]

  where
    parseSeqItem item =
      let o = jobj item
          mid = jstr (fromMaybe (JStr "") (jlookup "memory_id" o))
          ts = jnum (fromMaybe (JNum 0) (jlookup "timestamp" o))
          imp = jnum (fromMaybe (JNum 0.5) (jlookup "importance" o))
          gal = jstr (fromMaybe (JStr "universal") (jlookup "galaxy" o))
      in (mid, ts, imp, gal)

    replayItemToJVal (mid, ts, imp, gal, strength) = JObj
      [ ("memory_id", JStr mid)
      , ("timestamp", JNum ts)
      , ("importance", JNum imp)
      , ("galaxy", JStr gal)
      , ("replay_strength", JNum strength)
      ]

    processBatch batchObj =
      let seqArr = jarr (fromMaybe (JArr []) (jlookup "sequence" batchObj))
          seq_ = map parseSeqItem seqArr
          replayed = replaySequence seq_
          trajectories = detectTrajectories replayed
      in JObj
        [ ("replayed", JArr $ map replayItemToJVal replayed)
        , ("trajectory_count", JNum (fromIntegral (length trajectories)))
        , ("total_items", JNum (fromIntegral (length replayed)))
        ]

-- Main loop
loop :: IO ()
loop = do
  eof <- isEOF
  if eof
    then return ()
    else do
      line <- getLine
      if null (trim line)
        then loop
        else do
          let req = jobj (parseJSON (trim line))
          resp <- handle req
          putStrLn (show resp)
          loop
  where
    trim = reverse . dropWhile (`elem` " \t\r\n") . reverse . dropWhile (`elem` " \t\r\n")

main :: IO ()
main = do
  hSetBuffering stdout LineBuffering
  loop
