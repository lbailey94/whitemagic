"""dispatch_intelligence.py — Intelligence, knowledge-graph, embeddings, and cognitive tools.

Domain slice imported by dispatch_table.py.
"""

from collections.abc import Callable
from typing import Any

from whitemagic.tools.dispatch_core import LazyHandler

DISPATCH_INTELLIGENCE: dict[str, Callable[..., dict[str, Any]]] = {
    "thought_clone": LazyHandler("misc", "handle_thought_clone"),
    "coherence_boost": LazyHandler("misc", "handle_coherence_boost"),
    "anti_loop_check": LazyHandler("misc", "handle_anti_loop_check"),
    "token_report": LazyHandler("misc", "handle_token_report"),
    "solve_optimization": LazyHandler("solver", "handle_solve_optimization"),
    "simd.cosine": LazyHandler("simd", "handle_simd_cosine"),
    "simd.batch": LazyHandler("simd", "handle_simd_batch"),
    "simd.status": LazyHandler("simd", "handle_simd_status"),
    "hexagram.simd_execute": LazyHandler("simd", "handle_hexagram_simd_execute"),
    "hexagram.dispatch": LazyHandler("simd", "handle_hexagram_dispatch"),
    "hexagram.boltzmann_select": LazyHandler(
        "simd", "handle_hexagram_boltzmann_select"
    ),
    "kg.extract": LazyHandler("knowledge_graph", "handle_kg_extract"),
    "kg.query": LazyHandler("knowledge_graph", "handle_kg_query"),
    "kg.top": LazyHandler("knowledge_graph", "handle_kg_top"),
    "kg.status": LazyHandler("knowledge_graph", "handle_kg_status"),
    "kg2.extract": LazyHandler("knowledge_graph", "handle_kg2_extract"),
    "kg2.batch": LazyHandler("knowledge_graph", "handle_kg2_batch"),
    "kg2.entity": LazyHandler("knowledge_graph", "handle_kg2_entity"),
    "kg2.stats": LazyHandler("knowledge_graph", "handle_kg2_stats"),
    "embedding.daemon_start": LazyHandler(
        "knowledge_graph", "handle_embedding_daemon_start"
    ),
    "embedding.daemon_stop": LazyHandler(
        "knowledge_graph", "handle_embedding_daemon_stop"
    ),
    "embedding.daemon_status": LazyHandler(
        "knowledge_graph", "handle_embedding_daemon_status"
    ),
    "embedding.daemon_process": LazyHandler(
        "knowledge_graph", "handle_embedding_daemon_process"
    ),
    "rust_audit": LazyHandler("rust_bridge", "handle_rust_audit"),
    "rust_compress": LazyHandler("rust_bridge", "handle_rust_compress"),
    "rust_similarity": LazyHandler("rust_bridge", "handle_rust_similarity"),
    "rust_status": LazyHandler("rust_bridge", "handle_rust_status"),
    "dream": LazyHandler("dreaming", "handle_dream"),
    "dream_start": LazyHandler("dreaming", "handle_dream_start"),
    "dream_stop": LazyHandler("dreaming", "handle_dream_stop"),
    "dream_status": LazyHandler("dreaming", "handle_dream_status"),
    "dream_now": LazyHandler("dreaming", "handle_dream_now"),
    "dream.list": LazyHandler("dream_artifacts", "handle_dream_list"),
    "dream.read": LazyHandler("dream_artifacts", "handle_dream_read"),
    "dream.promote": LazyHandler("dream_artifacts", "handle_dream_promote"),
    "dream.expire": LazyHandler("dream_artifacts", "handle_dream_expire"),
    "cache.status": LazyHandler("cache_coherence", "handle_cache_status"),
    "cache.flush": LazyHandler("cache_coherence", "handle_cache_flush"),
    "zodiac.status": LazyHandler("zodiac_progression", "handle_zodiac_status"),
    "zodiac.activate": LazyHandler("zodiac_progression", "handle_zodiac_activate"),
    "zodiac.council": LazyHandler("zodiac_progression", "handle_zodiac_council"),
    "zodiac.stats": LazyHandler("zodiac_progression", "handle_zodiac_stats"),
    "bitnet_infer": LazyHandler("bitnet", "handle_bitnet_infer"),
    "bitnet_status": LazyHandler("bitnet", "handle_bitnet_status"),
    "edge_infer": LazyHandler("edge", "handle_edge_infer"),
    "edge_add_rule": LazyHandler("edge", "handle_edge_add_rule"),
    "edge_batch_infer": LazyHandler("edge", "handle_edge_batch_infer"),
    "edge_stats": LazyHandler("edge", "handle_edge_stats"),
    "kaizen_analyze": LazyHandler("synthesis", "handle_kaizen_analyze"),
    "kaizen_apply_fixes": LazyHandler("synthesis", "handle_kaizen_apply_fixes"),
    "serendipity_surface": LazyHandler("synthesis", "handle_serendipity_surface"),
    "serendipity_mark_accessed": LazyHandler(
        "synthesis", "handle_serendipity_mark_accessed"
    ),
    "pattern_search": LazyHandler("synthesis", "handle_pattern_search"),
    "cluster_stats": LazyHandler("synthesis", "handle_cluster_stats"),
    "list_cascade_patterns": LazyHandler("synthesis", "handle_list_cascade_patterns"),
    "causal.mine": LazyHandler("pattern_engines", "handle_causal_mine"),
    "causal.stats": LazyHandler("pattern_engines", "handle_causal_stats"),
    "emergence.scan": LazyHandler("pattern_engines", "handle_emergence_scan"),
    "emergence.status": LazyHandler("pattern_engines", "handle_emergence_status"),
    "association.mine": LazyHandler("pattern_engines", "handle_association_mine"),
    "association.mine_semantic": LazyHandler(
        "pattern_engines", "handle_association_mine_semantic"
    ),
    "constellation.detect": LazyHandler(
        "pattern_engines", "handle_constellation_detect"
    ),
    "constellation.stats": LazyHandler("pattern_engines", "handle_constellation_stats"),
    "constellation.merge": LazyHandler("pattern_engines", "handle_constellation_merge"),
    "satkona.fuse": LazyHandler("pattern_engines", "handle_satkona_fuse"),
    "reasoning.multispectral": LazyHandler(
        "pattern_engines", "handle_reasoning_multispectral"
    ),
    "novelty.detect": LazyHandler("pattern_engines", "handle_novelty_detect"),
    "novelty.stats": LazyHandler("pattern_engines", "handle_novelty_stats"),
    "bridge.synthesize": LazyHandler("pattern_engines", "handle_bridge_synthesize"),
    "galactic.sweep": LazyHandler("pattern_engines", "handle_galactic_sweep"),
    "galactic.stats": LazyHandler("pattern_engines", "handle_galactic_stats"),
    "guideline.evolve": LazyHandler("pattern_engines", "handle_guideline_evolve"),
    "elemental.optimize": LazyHandler("pattern_engines", "handle_elemental_optimize"),
    "pattern_consciousness.status": LazyHandler(
        "pattern_engines", "handle_pattern_consciousness_status"
    ),
    "reasoning.bicameral": LazyHandler("cyberbrain", "handle_bicameral_reason"),
    "drive.snapshot": LazyHandler("cyberbrain", "handle_drive_snapshot"),
    "drive.event": LazyHandler("cyberbrain", "handle_drive_event"),
    "selfmodel.forecast": LazyHandler("cyberbrain", "handle_selfmodel_forecast"),
    "selfmodel.alerts": LazyHandler("cyberbrain", "handle_selfmodel_alerts"),
    "worker.status": LazyHandler("cyberbrain", "handle_worker_status"),
    "rerank": LazyHandler("cognitive_extensions", "handle_rerank"),
    "rerank.status": LazyHandler("cognitive_extensions", "handle_rerank_status"),
    "working_memory.attend": LazyHandler(
        "cognitive_extensions", "handle_working_memory_attend"
    ),
    "working_memory.context": LazyHandler(
        "cognitive_extensions", "handle_working_memory_context"
    ),
    "working_memory.status": LazyHandler(
        "cognitive_extensions", "handle_working_memory_status"
    ),
    "reconsolidation.mark": LazyHandler(
        "cognitive_extensions", "handle_reconsolidation_mark"
    ),
    "reconsolidation.update": LazyHandler(
        "cognitive_extensions", "handle_reconsolidation_update"
    ),
    "reconsolidation.status": LazyHandler(
        "cognitive_extensions", "handle_reconsolidation_status"
    ),
    "jit_research": LazyHandler("v14_2_handlers", "handle_jit_research"),
    "jit_research.stats": LazyHandler("v14_2_handlers", "handle_jit_research_stats"),
    "narrative.compress": LazyHandler("v14_2_handlers", "handle_narrative_compress"),
    "narrative.stats": LazyHandler("v14_2_handlers", "handle_narrative_stats"),
    "hermit.status": LazyHandler("v14_2_handlers", "handle_hermit_status"),
    "hermit.assess": LazyHandler("v14_2_handlers", "handle_hermit_assess"),
    "hermit.withdraw": LazyHandler("v14_2_handlers", "handle_hermit_withdraw"),
    "hermit.mediate": LazyHandler("v14_2_handlers", "handle_hermit_mediate"),
    "hermit.resolve": LazyHandler("v14_2_handlers", "handle_hermit_resolve"),
    "hermit.verify_ledger": LazyHandler(
        "v14_2_handlers", "handle_hermit_verify_ledger"
    ),
    "hermit.check_access": LazyHandler("v14_2_handlers", "handle_hermit_check_access"),
    "green.report": LazyHandler("v14_2_handlers", "handle_green_report"),
    "green.record": LazyHandler("v14_2_handlers", "handle_green_record"),
    "cognitive.mode": LazyHandler("v14_2_handlers", "handle_cognitive_mode"),
    "cognitive.set": LazyHandler("v14_2_handlers", "handle_cognitive_set"),
    "cognitive.hints": LazyHandler("v14_2_handlers", "handle_cognitive_hints"),
    "cognitive.stats": LazyHandler("v14_2_handlers", "handle_cognitive_stats"),
    "context.pack": LazyHandler("context_optimizer", "handle_context_pack"),
    "context.status": LazyHandler("context_optimizer", "handle_context_status"),
    "prompt.render": LazyHandler("prompts", "handle_prompt_render"),
    "prompt.list": LazyHandler("prompts", "handle_prompt_list"),
    "prompt.reload": LazyHandler("prompts", "handle_prompt_reload"),
    "vector.search": LazyHandler("vector_search", "handle_vector_search"),
    "vector.index": LazyHandler("vector_search", "handle_vector_index"),
    "vector.status": LazyHandler("vector_search", "handle_vector_status"),
    "fragment.search": LazyHandler("fragment", "handle_fragment_search"),
    "fragment.index": LazyHandler("fragment", "handle_fragment_index"),
    "fragment.status": LazyHandler("fragment", "handle_fragment_status"),
    "fragment.query": LazyHandler("fragment", "handle_fragment_query"),
    "learning.patterns": LazyHandler("learning", "handle_learning_patterns"),
    "learning.suggest": LazyHandler("learning", "handle_learning_suggest"),
    "learning.status": LazyHandler("learning", "handle_learning_status"),
    "grimoire_list": LazyHandler("misc", "handle_grimoire_list"),
    "grimoire_suggest": LazyHandler("grimoire", "handle_grimoire_suggest"),
    "grimoire_cast": LazyHandler("grimoire", "handle_grimoire_cast"),
    "grimoire_recommend": LazyHandler("grimoire", "handle_grimoire_recommend"),
    "grimoire_auto_status": LazyHandler("grimoire", "handle_grimoire_auto_status"),
    "grimoire_walkthrough": LazyHandler(
        "grimoire_walkthrough", "handle_grimoire_walkthrough"
    ),
    "grimoire_read": LazyHandler("misc", "handle_grimoire_read"),
    "ollama.models": LazyHandler("ollama", "handle_ollama_models"),
    "ollama.generate": LazyHandler("ollama", "handle_ollama_generate"),
    "ollama.chat": LazyHandler("ollama", "handle_ollama_chat"),
    "ollama.agent": LazyHandler("ollama", "handle_ollama_agent"),
    "voice_audit.scan": LazyHandler("voice_audit", "handle_voice_audit_scan"),
    "voice_audit.status": LazyHandler("voice_audit", "handle_voice_audit_status"),
    "voice_audit.quarantine_list": LazyHandler(
        "voice_audit", "handle_voice_audit_quarantine_list"
    ),
    "corpus_callosum.debate": LazyHandler(
        "corpus_callosum", "handle_corpus_callosum_debate"
    ),
    "corpus_callosum.status": LazyHandler(
        "corpus_callosum", "handle_corpus_callosum_status"
    ),
    "think": LazyHandler("aliases", "handle_think"),
    "check": LazyHandler("aliases", "handle_check"),
    "execute_cascade": LazyHandler("misc", "handle_execute_cascade"),
}
