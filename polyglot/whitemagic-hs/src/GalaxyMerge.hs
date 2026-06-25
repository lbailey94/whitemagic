{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE DeriveAnyClass #-}

-- |
-- Module: GalaxyMerge
-- Description: Type-safe galaxy merge operations with conflict resolution
--
-- Provides algebraic data types for galaxy schemas, composition rules,
-- and merge conflict resolution. All merge operations are type-safe and
-- validated against schema constraints.
module GalaxyMerge
  ( GalaxyID(..)
  , MemoryID(..)
  , MemoryRecord(..)
  , GalaxySchema(..)
  , MergeConflict(..)
  , MergeStrategy(..)
  , MergeResult(..)
  , mergeGalaxies
  , validateMerge
  , resolveConflict
  , defaultSchema
  , schemaCompatible
  ) where

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Data.Maybe (fromMaybe)
import GHC.Generics (Generic)

-- | Type-safe galaxy identifier
newtype GalaxyID = GalaxyID String
  deriving (Show, Eq, Ord, Generic)

-- | Type-safe memory identifier
newtype MemoryID = MemoryID String
  deriving (Show, Eq, Ord, Generic)

-- | A memory record in a galaxy
data MemoryRecord = MemoryRecord
  { memId :: MemoryID
  , memContent :: String
  , memImportance :: Double
  , memGalaxy :: GalaxyID
  , memTimestamp :: String  -- ISO-8601
  } deriving (Show, Eq, Generic)

-- | Galaxy schema defines what types a galaxy accepts
data GalaxySchema = GalaxySchema
  { schemaGalaxyId :: GalaxyID
  , schemaAllowedTypes :: [String]  -- e.g. ["LONG_TERM", "PATTERN"]
  , schemaMinImportance :: Double
  , schemaMaxMemories :: Maybe Int  -- Nothing = unlimited
  } deriving (Show, Eq, Generic)

-- | Merge conflict types
data MergeConflict
  = ConflictDuplicate MemoryID       -- Same ID in both galaxies
  | ConflictSchemaMismatch GalaxyID   -- Schemas incompatible
  | ConflictImportanceClash MemoryID  -- Different importance for same ID
  | ConflictCapacityExceeded GalaxyID -- Would exceed max memories
  deriving (Show, Eq, Generic)

-- | Strategy for resolving conflicts
data MergeStrategy
  = StrategySourceWins    -- Source galaxy wins conflicts
  | StrategyTargetWins    -- Target galaxy wins conflicts
  | StrategyHigherImportance -- Higher importance wins
  | StrategyLatestTimestamp -- Most recent timestamp wins
  deriving (Show, Eq, Generic)

-- | Result of a merge operation
data MergeResult = MergeResult
  { mergeSuccess :: Bool
  , mergeConflicts :: [MergeConflict]
  , mergeResolved :: [MemoryID]  -- IDs that had conflicts resolved
  , mergeAdded :: [MemoryID]     -- IDs newly added
  , mergeSkipped :: [MemoryID]   -- IDs skipped (duplicates without conflict)
  , mergeTotal :: Int
  } deriving (Show, Eq, Generic)

-- | Default schema for a galaxy
defaultSchema :: GalaxyID -> GalaxySchema
defaultSchema gid = GalaxySchema
  { schemaGalaxyId = gid
  , schemaAllowedTypes = ["SHORT_TERM", "LONG_TERM", "PATTERN", "WORKING"]
  , schemaMinImportance = 0.0
  , schemaMaxMemories = Nothing
  }

-- | Check if two schemas are compatible for merging
schemaCompatible :: GalaxySchema -> GalaxySchema -> Bool
schemaCompatible a b =
  schemaGalaxyId a == schemaGalaxyId b ||
  (schemaMinImportance a <= schemaMaxImportanceB &&
   schemaMinImportance b <= schemaMaxImportanceA)
  where
    maxImportanceA = 1.0  -- Max importance is always 1.0
    maxImportanceB = 1.0
    schemaMaxImportanceA = maxImportanceA
    schemaMaxImportanceB = maxImportanceB

-- | Validate a merge before executing
validateMerge :: GalaxySchema -> Map MemoryID MemoryRecord
              -> GalaxySchema -> Map MemoryID MemoryRecord
              -> [MergeConflict]
validateMerge targetSchema targetMemories sourceSchema sourceMemories =
  let
    -- Check schema compatibility
    schemaConflicts = if schemaCompatible targetSchema sourceSchema
                      then []
                      else [ConflictSchemaMismatch (schemaGalaxyId sourceSchema)]

    -- Check for duplicates
    duplicateConflicts = map ConflictDuplicate
      $ filter (`Map.member` targetMemories)
      $ Map.keys sourceMemories

    -- Check for importance clashes on duplicates
    importanceConflicts = concatMap checkImportance
      $ Map.keys sourceMemories
      where
        checkImportance mid =
          case (Map.lookup mid targetMemories, Map.lookup mid sourceMemories) of
            (Just t, Just s) ->
              if memImportance t /= memImportance s
              then [ConflictImportanceClash mid]
              else []
            _ -> []

    -- Check capacity
    capacityConflicts = case schemaMaxMemories targetSchema of
      Nothing -> []
      Just maxN ->
        let total = Map.size targetMemories + Map.size sourceMemories
                    - length duplicateConflicts
        in if total > maxN
           then [ConflictCapacityExceeded (schemaGalaxyId targetSchema)]
           else []
  in
    schemaConflicts ++ duplicateConflicts ++ importanceConflicts ++ capacityConflicts

-- | Resolve a single conflict using the given strategy
resolveConflict :: MergeStrategy -> MemoryRecord -> MemoryRecord
                -> MergeConflict -> MemoryRecord
resolveConflict strategy source target conflict =
  case conflict of
    ConflictDuplicate _ -> case strategy of
      StrategySourceWins -> source
      StrategyTargetWins -> target
      StrategyHigherImportance ->
        if memImportance source >= memImportance target
        then source else target
      StrategyLatestTimestamp ->
        if memTimestamp source >= memTimestamp target
        then source else target
    ConflictImportanceClash _ -> case strategy of
      StrategySourceWins -> source
      StrategyTargetWins -> target
      StrategyHigherImportance ->
        if memImportance source >= memImportance target
        then source else target
      StrategyLatestTimestamp ->
        if memTimestamp source >= memTimestamp target
        then source else target
    _ -> target  -- Keep target for other conflict types

-- | Merge two galaxies with conflict resolution
mergeGalaxies :: GalaxySchema -> Map MemoryID MemoryRecord
              -> GalaxySchema -> Map MemoryID MemoryRecord
              -> MergeStrategy
              -> MergeResult
mergeGalaxies targetSchema targetMemories sourceSchema sourceMemories strategy =
  let
    conflicts = validateMerge targetSchema targetMemories
                                 sourceSchema sourceMemories

    hasBlockingConflicts = any isBlocking conflicts
      where
        isBlocking (ConflictSchemaMismatch _) = True
        isBlocking (ConflictCapacityExceeded _) = True
        isBlocking _ = False

    -- Partition source memories into new and duplicate
    (newMemories, dupMemories) = Map.partitionWithKey
      (\mid _ -> not (mid `Map.member` targetMemories))
      sourceMemories

    -- Resolve conflicts for duplicates
    resolvedMemories = Map.mapWithKey
      (\mid sourceMem ->
        case Map.lookup mid targetMemories of
          Just targetMem ->
            let conflict = ConflictDuplicate mid
            in resolveConflict strategy sourceMem targetMem conflict
          Nothing -> sourceMem
      ) dupMemories

    -- Determine which duplicates were actually changed (resolved)
    resolvedIds = filter
      (\mid -> case (Map.lookup mid dupMemories, Map.lookup mid targetMemories) of
        (Just s, Just t) -> s /= t
        _ -> False)
      (Map.keys dupMemories)

    -- Skipped = duplicates where source == target (no change needed)
    skippedIds = filter
      (\mid -> case (Map.lookup mid dupMemories, Map.lookup mid targetMemories) of
        (Just s, Just t) -> s == t
        _ -> False)
      (Map.keys dupMemories)

    addedIds = Map.keys newMemories

    totalAdded = Map.size newMemories
    totalResolved = length resolvedIds
    totalSkipped = length skippedIds
    total = totalAdded + totalResolved

  in MergeResult
    { mergeSuccess = not hasBlockingConflicts
    , mergeConflicts = conflicts
    , mergeResolved = resolvedIds
    , mergeAdded = addedIds
    , mergeSkipped = skippedIds
    , mergeTotal = total
    }
