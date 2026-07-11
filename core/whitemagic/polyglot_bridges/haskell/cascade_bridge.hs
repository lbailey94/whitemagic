#!/usr/bin/env runhaskell
-- WhiteMagic Haskell Cascade DAG Verifier
-- JSON stdio bridge for cycle detection in cascade trigger graphs
--
-- Methods:
--   ping -> {"status":"ok","backend":"haskell-cascade"}
--   detect_cycles -> {"status":"ok","cycles":[...],"safe":bool}
--   is_safe -> {"status":"ok","safe":bool}

import System.IO
import Data.List (intercalate, nub, isPrefixOf)

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

jarr :: JVal -> [JVal]
jarr (JArr a) = a
jarr _ = []

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
dropSpaces = dropWhile (`elem` " \t\n\r")

parseVal :: String -> Maybe (JVal, String)
parseVal s = case dropSpaces s of
  ('{':rest) -> parseObj rest
  ('[':rest) -> parseArr rest
  ('"':rest) -> case parseStr rest of
    Just (str, rest') -> Just (JStr str, rest')
    Nothing -> Nothing
  ('t':rest) | "true" `isPrefixOf` ('t':rest) -> Just (JBool True, rest)
  ('f':rest) | "false" `isPrefixOf` ('f':rest) -> Just (JBool False, rest)
  ('n':rest) | "null" `isPrefixOf` ('n':rest) -> Just (JNull, rest)
  (c:rest) | c `elem` "-0123456789." -> parseNum (c:rest)
  _ -> Nothing

parseStr :: String -> Maybe (String, String)
parseStr s = go s
  where
    go [] = Nothing
    go ('"':rest) = Just ("", rest)
    go ('\\':c:rest) = case go rest of
      Just (str, rest') -> Just (c:str, rest')
      Nothing -> Nothing
    go (c:rest) = case go rest of
      Just (str, rest') -> Just (c:str, rest')
      Nothing -> Nothing

parseNum :: String -> Maybe (JVal, String)
parseNum s =
  let (numStr, rest) = span (`elem` "-0123456789.eE+") s
  in case reads numStr :: [(Double, String)] of
    [(n, _)] -> Just (JNum n, rest)
    _ -> Nothing

parseObj :: String -> Maybe (JVal, String)
parseObj s = go (dropSpaces s) []
  where
    go ('}':rest) acc = Just (JObj (reverse acc), rest)
    go rest acc = do
      (key, rest1) <- case parseVal rest of
        Just (JStr k, r) -> Just (k, r)
        _ -> Nothing
      rest2 <- case dropSpaces rest1 of
        (':':r) -> Just r
        _ -> Nothing
      (val, rest3) <- parseVal rest2
      case dropSpaces rest3 of
        (',':r) -> go (dropSpaces r) ((key, val):acc)
        ('}':r) -> Just (JObj (reverse ((key, val):acc)), r)
        _ -> Nothing

parseArr :: String -> Maybe (JVal, String)
parseArr s = go (dropSpaces s) []
  where
    go (']':rest) acc = Just (JArr (reverse acc), rest)
    go rest acc = do
      (val, rest1) <- parseVal rest
      case dropSpaces rest1 of
        (',':r) -> go (dropSpaces r) (val:acc)
        (']':r) -> Just (JArr (reverse (val:acc)), r)
        _ -> Nothing

-- ---- Cascade Graph ----

-- Extract trigger → target edges from JSON triggers array
extractEdges :: JVal -> [(String, String)]
extractEdges triggers = concatMap extractFromTrigger (jarr triggers)
  where
    extractFromTrigger t =
      let triggerEvent = jstr <$> jlookup "trigger_event" (jobj t)
          targetEvents = jarr <$> jlookup "target_events" (jobj t)
      in case (triggerEvent, targetEvents) of
        (Just te, Just tes) -> [(te, jstr target) | target <- tes]
        _ -> []

-- DFS-based cycle detection
detectCycles :: [(String, String)] -> [[String]]
detectCycles edges = cycles
  where
    nodes = nub (map fst edges ++ map snd edges)
    adj n = [m | (f, m) <- edges, f == n]

    dfs visited path onPath node =
      if node `elem` onPath
        then [reverse (takeWhile (/= node) (reverse path)) ++ [node]]
        else if node `elem` visited
          then []
          else concatMap
                 (dfs (node:visited) (node:path) (node:onPath))
                 (adj node)

    cycles = concatMap (dfs [] [] []) nodes

-- ---- Request Handler ----

handleRequest :: String -> String
handleRequest line =
  case parseJson line of
    Just req ->
      let method = jstr <$> jlookup "method" (jobj req)
          params = case jlookup "params" (jobj req) of
            Just p -> p
            Nothing -> JObj []
      in case method of
        Just "ping" ->
          show (JObj [("status", JStr "ok"), ("result", JObj [("backend", JStr "haskell-cascade")])])
        Just "detect_cycles" ->
          let triggers = case jlookup "triggers" (jobj params) of
                Just t -> t
                Nothing -> JArr []
              edges = extractEdges triggers
              cyc = detectCycles edges
              safe = null cyc
              jsonCycles = JArr [JArr [JStr n | n <- c] | c <- cyc]
          in show (JObj [("status", JStr "ok"), ("result", JObj [("cycles", jsonCycles), ("safe", JBool safe)])])
        Just "is_safe" ->
          let triggers = case jlookup "triggers" (jobj params) of
                Just t -> t
                Nothing -> JArr []
              edges = extractEdges triggers
              safe = null (detectCycles edges)
          in show (JObj [("status", JStr "ok"), ("result", JObj [("safe", JBool safe)])])
        Just m ->
          show (JObj [("status", JStr "error"), ("error", JStr ("Unknown method: " ++ m))])
        Nothing ->
          show (JObj [("status", JStr "error"), ("error", JStr "Missing method")])
    Nothing ->
      show (JObj [("status", JStr "error"), ("error", JStr "Invalid JSON")])

-- ---- Main loop ----

main :: IO ()
main = do
  hSetBuffering stdout LineBuffering
  interact (unlines . map handleRequest . lines)
