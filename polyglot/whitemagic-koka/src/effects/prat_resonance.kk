// prat_resonance - Session-level Gana resonance state (S022 Phase 1 VC2)
// Ported from prat_resonance.py

module prat_resonance

import std/time
import std/num/random
import std/core/vector
import std/num/float64
import std/os/readline

// ═══════════════════════════════════════════════════════════════════════════
// Resonance Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect resonance
  // Core resonance operations
  fun get-last-snapshot(): snapshot
  fun record-snapshot(snap: snapshot): ()
  fun get-call-count(): int
  fun get-gana-counts(): list<(string, int)>
  fun get-recent-history(limit: int): list<snapshot>
  fun reset-state(): ()
  
  // Lunar and harmony state
  fun get-lunar-phase(): float64
  fun get-lunar-mansion(): int
  fun get-harmony-score(): float64
  fun get-guna-tag(): string

// ═══════════════════════════════════════════════════════════════════════════
// Snapshot type - captures context from a single PRAT invocation
// ═══════════════════════════════════════════════════════════════════════════

struct snapshot
  gana-name: string
  tool-name: string
  operation: string
  output-preview: string
  timestamp: float64
  lunar-phase: float64
  lunar-mansion-num: int
  harmony-score: float64
  guna-tag: string
  quadrant: string
  successor-hint: string

fun snapshot-to-json(s: snapshot): string
  "{" ++
  "\"gana_name\": \"" ++ s.gana-name ++ "\"," ++
  "\"tool_name\": \"" ++ s.tool-name ++ "\"," ++
  "\"operation\": \"" ++ s.operation ++ "\"," ++
  "\"output_preview\": \"" ++ s.output-preview ++ "\"," ++
  "\"timestamp\": " ++ s.timestamp.show ++ "," ++
  "\"lunar_phase\": " ++ s.lunar-phase.show ++ "," ++
  "\"lunar_mansion_num\": " ++ s.lunar-mansion-num.show ++ "," ++
  "\"harmony_score\": " ++ s.harmony-score.show ++ "," ++
  "\"guna_tag\": \"" ++ s.guna-tag ++ "\"," ++
  "\"quadrant\": \"" ++ s.quadrant ++ "\"," ++
  "\"successor_hint\": \"" ++ s.successor-hint ++ "\"" ++
  "}"

// ═══════════════════════════════════════════════════════════════════════════
// Gana metadata (matching prat_router.py)
// ═══════════════════════════════════════════════════════════════════════════

struct ganainfo
  mansion-num: int
  quadrant: string
  meaning: string
  garden: string
  chinese: string
  pinyin: string

val gana-metadata : list<(string, ganainfo)> = 
  [
    ("gana_horn", Ganainfo(1, "East", "Sharp initiation", "Courage", "角", "Jiao")),
    ("gana_neck", Ganainfo(2, "East", "Stability", "Practice", "亢", "Kang")),
    ("gana_root", Ganainfo(3, "East", "Foundation", "Truth", "氐", "Di")),
    ("gana_room", Ganainfo(4, "East", "Enclosure", "Sanctuary", "房", "Fang")),
    ("gana_heart", Ganainfo(5, "East", "Vital pulse", "Love", "心", "Xin")),
    ("gana_tail", Ganainfo(6, "East", "Passionate drive", "Metal", "尾", "Wei")),
    ("gana_winnowing_basket", Ganainfo(7, "East", "Separation", "Wisdom", "箕", "Ji")),
    ("gana_ghost", Ganainfo(8, "South", "Introspection", "Grief", "鬼", "Gui")),
    ("gana_willow", Ganainfo(9, "South", "Flexibility", "Play", "柳", "Liu")),
    ("gana_star", Ganainfo(10, "South", "Illumination", "Beauty", "星", "Xing")),
    ("gana_extended_net", Ganainfo(11, "South", "Connectivity", "Connection", "张", "Zhang")),
    ("gana_wings", Ganainfo(12, "South", "Expansion", "Adventure", "翼", "Yi")),
    ("gana_chariot", Ganainfo(13, "South", "Movement", "Transformation", "轸", "Zhen")),
    ("gana_abundance", Ganainfo(14, "South", "Surplus", "Joy", "豐", "Feng")),
    ("gana_straddling_legs", Ganainfo(15, "West", "Balance", "Patience", "奎", "Kui")),
    ("gana_mound", Ganainfo(16, "West", "Accumulation", "Gratitude", "娄", "Lou")),
    ("gana_stomach", Ganainfo(17, "West", "Nourishment", "Healing", "胃", "Wei")),
    ("gana_hairy_head", Ganainfo(18, "West", "Detail", "Presence", "昴", "Mao")),
    ("gana_net", Ganainfo(19, "West", "Capture", "Mystery", "毕", "Bi")),
    ("gana_turtle_beak", Ganainfo(20, "West", "Precision", "Voice", "觜", "Zui")),
    ("gana_three_stars", Ganainfo(21, "West", "Judgment", "Dharma", "参", "Shen")),
    ("gana_dipper", Ganainfo(22, "North", "Governance", "Awe", "斗", "Dou")),
    ("gana_ox", Ganainfo(23, "North", "Endurance", "Reverence", "牛", "Niu")),
    ("gana_girl", Ganainfo(24, "North", "Nurture", "Wonder", "女", "Nu")),
    ("gana_void", Ganainfo(25, "North", "Emptiness", "Stillness", "虚", "Xu")),
    ("gana_roof", Ganainfo(26, "North", "Shelter", "Protection", "危", "Wei")),
    ("gana_encampment", Ganainfo(27, "North", "Structure", "Sangha", "室", "Shi")),
    ("gana_wall", Ganainfo(28, "North", "Boundaries", "Air", "壁", "Bi"))
  ]

val gana-order : list<string> = 
  [
    "gana_horn", "gana_neck", "gana_root", "gana_room", "gana_heart",
    "gana_tail", "gana_winnowing_basket", "gana_ghost", "gana_willow",
    "gana_star", "gana_extended_net", "gana_wings", "gana_chariot",
    "gana_abundance", "gana_straddling_legs", "gana_mound", "gana_stomach",
    "gana_hairy_head", "gana_net", "gana_turtle_beak", "gana_three_stars",
    "gana_dipper", "gana_ox", "gana_girl", "gana_void", "gana_roof",
    "gana_encampment", "gana_wall"
  ]

fun get-gana-meta(gana-name: string): ganainfo
  match gana-metadata.find(fn(p) p.fst == gana-name)
    Just((_, meta)) -> meta
    Nothing -> Ganainfo(0, "Unknown", gana-name, "None", "?", "?")

fun get-predecessor(gana-name: string): string
  val idx = gana-order.index-of(fn(g) g == gana-name)
  if idx >= 0 then
    match list/drop(gana-order, (idx - 1 + 28) % 28).head
      Just(g) -> g
      Nothing -> "gana_horn"
  else
    "gana_horn"

fun get-successor(gana-name: string): string
  val idx = gana-order.index-of(fn(g) g == gana-name)
  if idx >= 0 then
    match list/drop(gana-order, (idx + 1) % 28).head
      Just(g) -> g
      Nothing -> "gana_horn"
  else
    "gana_horn"

// ═══════════════════════════════════════════════════════════════════════════
// Resonance state management
// ═══════════════════════════════════════════════════════════════════════════

// State record for resonance tracking
struct resonance-state
  last-snapshot: maybe<snapshot>
  history: list<snapshot>
  gana-counts: list<(string, int)>
  session-calls: int

fun empty-state(): resonance-state
  Resonance-state(Nothing, [], [], 0)

fun record-in-state(st: resonance-state, snap: snapshot): resonance-state
  val new-counts = match st.gana-counts.find(fn(p) p.fst == snap.gana-name)
    Just((name, count)) -> 
      Cons((name, count + 1), st.gana-counts.filter(fn(p) p.fst != name))
    Nothing ->
      Cons((snap.gana-name, 1), st.gana-counts)
  
  Resonance-state(
    Just(snap),
    Cons(snap, st.history).take(50),  // Keep last 50
    new-counts,
    st.session-calls + 1
  )

// ═══════════════════════════════════════════════════════════════════════════
// Pure helper functions (outside handler to avoid effect inference issues)
// ═══════════════════════════════════════════════════════════════════════════

fun calculate-lunar-phase(): float64
  // Calculate approximate lunar phase from current time
  // Placeholder: returns 0.5 (full moon) for compilation
  0.5

fun calculate-lunar-mansion(): int
  // 28 mansions, cycle every ~27.3 days
  // Placeholder: returns 14 for compilation  
  14

fun calculate-harmony-score(counts: list<(string, int)>): float64
  // Calculate harmony based on gana balance
  val total = counts.foldl(0) fn(acc, p) acc + p.snd
  if total == 0 then 1.0
  else
    val variance = counts.foldl(0.0) fn(acc, p)
      val diff = float64(p.snd) - (float64(total) / 28.0)
      acc + (diff * diff)
    1.0 - (variance / float64(total * total))

fun calculate-guna-tag(phase: float64): string
  "rajasic"  // Placeholder - if/else chain has parsing issues

// ═══════════════════════════════════════════════════════════════════════════
// Resonance handler implementation
// ═══════════════════════════════════════════════════════════════════════════

fun handle-resonance(action: () -> <resonance> a): a
  var state := empty-state()
  
  handle action
    fun get-last-snapshot()
      match state.last-snapshot
        Just(s) -> s
        Nothing -> Snapshot("", "", "", "", 0.0, 0.0, 0, 1.0, "sattvic", "East", "")
    
    fun record-snapshot(snap)
      state := record-in-state(state, snap)
    
    fun get-call-count()
      state.session-calls
    
    fun get-gana-counts()
      state.gana-counts
    
    fun get-recent-history(limit)
      state.history.take(limit)
    
    fun reset-state()
      state := empty-state()
    
    fun get-lunar-phase()
      0.5
    
    fun get-lunar-mansion()
      14
    
    fun get-harmony-score()
      1.0
    
    fun get-guna-tag()
      "rajasic"

// ═══════════════════════════════════════════════════════════════════════════
// Resonance hint generation
// ═══════════════════════════════════════════════════════════════════════════

struct resonance-hints
  predecessor: string
  successor: string
  lunar-phase: float64
  lunar-mansion-num: int
  harmony-score: float64
  guna-tag: string
  quadrant: string

fun generate-hints(gana-name: string): <resonance> resonance-hints
  val pred = get-predecessor(gana-name)
  val succ = get-successor(gana-name)
  val meta = get-gana-meta(gana-name)
  
  Resonance-hints(
    pred,
    succ,
    get-lunar-phase(),
    get-lunar-mansion(),
    get-harmony-score(),
    get-guna-tag(),
    meta.quadrant
  )

fun hints-to-json(h: resonance-hints): string
  "{" ++
  "\"predecessor\": \"" ++ h.predecessor ++ "\"," ++
  "\"successor\": \"" ++ h.successor ++ "\"," ++
  "\"lunar_phase\": " ++ h.lunar-phase.show ++ "," ++
  "\"lunar_mansion_num\": " ++ h.lunar-mansion-num.show ++ "," ++
  "\"harmony_score\": " ++ h.harmony-score.show ++ "," ++
  "\"guna_tag\": \"" ++ h.guna-tag ++ "\"," ++
  "\"quadrant\": \"" ++ h.quadrant ++ "\"" ++
  "}"

// ═══════════════════════════════════════════════════════════════════════════
// Main PRAT resonance tracking (port of PratResonanceState.record)
// ═══════════════════════════════════════════════════════════════════════════

fun track-prat-invocation(
  gana-name: string,
  tool-name: string,
  operation: string,
  output: string
): <resonance> snapshot

  val hints = generate-hints(gana-name)
  val snap = Snapshot(
    gana-name,
    tool-name,
    operation,
    output,  // Preview only - full output
    0.0,  // Placeholder timestamp for compilation
    hints.lunar-phase,
    hints.lunar-mansion-num,
    hints.harmony-score,
    hints.guna-tag,
    hints.quadrant,
    hints.successor
  )
  
  record-snapshot(snap)
  snap

// Main entry point for FFI bridge - single request-response
fun main(): int
  val line = readline/read_line()
  if line != "" then
    println(handle-request(line))
  0

// Handle incoming JSON request
fun handle-request(request: string): string
  "{\"status\": \"ok\", \"echo\": " ++ request ++ "}"
