# Gana: gana_chariot

**127 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [abi.decode_calldata](../tools/abi.decode_calldata.md) | security | read | Decode raw calldata hex into selector and parameters |
| [abi.parse](../tools/abi.parse.md) | security | read | Parse Solidity ABI JSON into function signatures |
| [abi.summarize](../tools/abi.summarize.md) | security | read | Summarize an ABI — function count, events, signatures |
| [api.state_machine](../tools/api.state_machine.md) | security | read | Run API call sequences and detect state inconsistencies |
| [archaeology](../tools/archaeology.md) | archaeology | write | Unified file archaeology — track reads/writes, find unread/changed files, search |
| [archaeology_daily_digest](../tools/archaeology_daily_digest.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_daily_digest'. |
| [archaeology_find_changed](../tools/archaeology_find_changed.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_find_changed'. |
| [archaeology_find_unread](../tools/archaeology_find_unread.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_find_unread'. |
| [archaeology_have_read](../tools/archaeology_have_read.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_have_read'. |
| [archaeology_mark_read](../tools/archaeology_mark_read.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_mark_read'. |
| [archaeology_mark_written](../tools/archaeology_mark_written.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_mark_written'. |
| [archaeology_process_wisdom](../tools/archaeology_process_wisdom.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_process_wisdom'. |
| [archaeology_recent_reads](../tools/archaeology_recent_reads.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_recent_reads'. |
| [archaeology_report](../tools/archaeology_report.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_report'. |
| [archaeology_scan_directory](../tools/archaeology_scan_directory.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_scan_directory'. |
| [archaeology_search](../tools/archaeology_search.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_search'. |
| [archaeology_stats](../tools/archaeology_stats.md) | system | read | Dispatch-routable WhiteMagic tool 'archaeology_stats'. |
| [audit.report](../tools/audit.report.md) | security | read | Generate a professional audit report from findings |
| [autoswarm.campaign](../tools/autoswarm.campaign.md) | agent | write | Launch an evolutionary campaign (hypothesis → trial → result → share) |
| [autoswarm.start](../tools/autoswarm.start.md) | agent | write | Start continuous evolutionary autoswarm loop |
| [autoswarm.stop](../tools/autoswarm.stop.md) | agent | write | Stop continuous autoswarm loop |
| [browser_click](../tools/browser_click.md) | system | read | Dispatch-routable WhiteMagic tool 'browser_click'. |
| [browser_extract_dom](../tools/browser_extract_dom.md) | system | read | Dispatch-routable WhiteMagic tool 'browser_extract_dom'. |
| [browser_get_interactables](../tools/browser_get_interactables.md) | system | read | Dispatch-routable WhiteMagic tool 'browser_get_interactables'. |
| [browser_navigate](../tools/browser_navigate.md) | system | read | Dispatch-routable WhiteMagic tool 'browser_navigate'. |
| [browser_screenshot](../tools/browser_screenshot.md) | system | read | Dispatch-routable WhiteMagic tool 'browser_screenshot'. |
| [browser_session_status](../tools/browser_session_status.md) | system | read | Dispatch-routable WhiteMagic tool 'browser_session_status'. |
| [browser_type](../tools/browser_type.md) | system | read | Dispatch-routable WhiteMagic tool 'browser_type'. |
| [code.affected_by](../tools/code.affected_by.md) | system | read | Find all symbols that would be affected if the given symbol changes. Performs re |
| [code.communities](../tools/code.communities.md) | system | read | Detect communities (subsystems) in the code structure graph. Uses Louvain commun |
| [code.correlate](../tools/code.correlate.md) | system | read | Find memories that discuss a given code symbol. Searches for discussed_in edges  |
| [code.cross_repo_query](../tools/code.cross_repo_query.md) | system | read | Query across multiple repositories in a cross-repo graph. Requires repos to be a |
| [code.explain](../tools/code.explain.md) | system | read | Explain a symbol's role in the codebase: degree, incoming/outgoing edges, source |
| [code.export](../tools/code.export.md) | system | read | Export the code structure graph to Graphify-compatible graph.json format. Includ |
| [code.god_nodes](../tools/code.god_nodes.md) | system | read | List the most-connected symbols (highest degree centrality) in the code graph. T |
| [code.graph](../tools/code.graph.md) | system | read | Build or rebuild the code structure graph from source files. Extracts functions, |
| [code.import](../tools/code.import.md) | system | read | Import a Graphify-compatible graph.json file into the code structure graph. Supp |
| [code.path](../tools/code.path.md) | system | read | Trace the call path between two symbols (A → B) in the code graph. Uses BFS on t |
| [code.query](../tools/code.query.md) | system | read | Natural language query against the code structure graph. Supports patterns like  |
| [code.stats](../tools/code.stats.md) | system | read | Get code structure graph statistics: node count, edge count, node types, edge ty |
| [code.subgraph](../tools/code.subgraph.md) | system | read | Extract the neighborhood around a symbol up to a given depth. Returns all nodes  |
| [codebase.find](../tools/codebase.find.md) | system | read | Find files by extension, tag, or path pattern in the codex galaxy. Faster than g |
| [codebase.recall](../tools/codebase.recall.md) | memory | read | Semantic recall from the codex galaxy. Searches file and chunk content memories  |
| [codebase.scan](../tools/codebase.scan.md) | system | read | Scan the codebase and ingest files + directory topology into the codex galaxy. F |
| [codebase.status](../tools/codebase.status.md) | system | read | Get codebase scan status — last scan time, file counts, extension breakdown, chu |
| [codebase.structure](../tools/codebase.structure.md) | system | read | Recall directory topology from the codex galaxy. Returns files and subdirectorie |
| [codegenome.fork](../tools/codegenome.fork.md) | system | read | Dispatch-routable WhiteMagic tool 'codegenome.fork'. |
| [codegenome.generate](../tools/codegenome.generate.md) | system | read | Dispatch-routable WhiteMagic tool 'codegenome.generate'. |
| [codegenome.list](../tools/codegenome.list.md) | system | read | Dispatch-routable WhiteMagic tool 'codegenome.list'. |
| [codegenome.status](../tools/codegenome.status.md) | system | read | Dispatch-routable WhiteMagic tool 'codegenome.status'. |
| [codegenome_validate](../tools/codegenome_validate.md) | system | read | Dispatch-routable WhiteMagic tool 'codegenome_validate'. |
| [deep_fetch](../tools/deep_fetch.md) | system | read | Dispatch-routable WhiteMagic tool 'deep_fetch'. |
| [dna_principles](../tools/dna_principles.md) | introspection | read | List all core DNA principles that govern WhiteMagic's immune system |
| [dna_validate](../tools/dna_validate.md) | system | read | Validate a proposed fix against WhiteMagic's core DNA principles. Checks for vio |
| [echidna.fuzz](../tools/echidna.fuzz.md) | security | read | Run Echidna property-based fuzzer on a Solidity contract |
| [echidna.status](../tools/echidna.status.md) | security | read | Check Echidna availability and configuration |
| [embedding.daemon_process](../tools/embedding.daemon_process.md) | system | read | Dispatch-routable WhiteMagic tool 'embedding.daemon_process'. |
| [embedding.daemon_start](../tools/embedding.daemon_start.md) | system | read | Dispatch-routable WhiteMagic tool 'embedding.daemon_start'. |
| [embedding.daemon_status](../tools/embedding.daemon_status.md) | system | read | Dispatch-routable WhiteMagic tool 'embedding.daemon_status'. |
| [embedding.daemon_stop](../tools/embedding.daemon_stop.md) | system | read | Dispatch-routable WhiteMagic tool 'embedding.daemon_stop'. |
| [external.repo_compare](../tools/external.repo_compare.md) | system | read | Dispatch-routable WhiteMagic tool 'external.repo_compare'. |
| [external.repo_scan](../tools/external.repo_scan.md) | system | read | Dispatch-routable WhiteMagic tool 'external.repo_scan'. |
| [external.wiki_query](../tools/external.wiki_query.md) | system | read | Dispatch-routable WhiteMagic tool 'external.wiki_query'. |
| [fix.apply](../tools/fix.apply.md) | security | write | Apply a fix to a file (dry-run by default) |
| [fix.generate](../tools/fix.generate.md) | security | read | Generate fix suggestions from STRATA findings |
| [foundry.build](../tools/foundry.build.md) | security | read | Build a Foundry project using forge build |
| [foundry.test](../tools/foundry.test.md) | security | read | Run Foundry tests with forge test |
| [foundry.test_json](../tools/foundry.test_json.md) | security | read | Run Foundry tests and return JSON output |
| [http_probe.get](../tools/http_probe.get.md) | security | read | Send an HTTP GET request |
| [http_probe.idor](../tools/http_probe.idor.md) | security | read | Probe for IDOR by iterating resource IDs |
| [http_probe.post](../tools/http_probe.post.md) | security | read | Send an HTTP POST request |
| [http_probe.sqli](../tools/http_probe.sqli.md) | security | read | Probe a URL parameter for SQL injection |
| [http_probe.ssrf](../tools/http_probe.ssrf.md) | security | read | Probe a URL parameter for SSRF |
| [http_probe.xss](../tools/http_probe.xss.md) | security | read | Probe a URL parameter for reflected XSS |
| [image_analyze](../tools/image_analyze.md) | system | read | Dispatch-routable WhiteMagic tool 'image_analyze'. |
| [kg.extract](../tools/kg.extract.md) | memory | write | Extract entities and relations from text into the knowledge graph (spaCy NER + r |
| [kg.query](../tools/kg.query.md) | memory | read | Query an entity and its connections in the knowledge graph |
| [kg.status](../tools/kg.status.md) | introspection | read | Get knowledge graph status — entity/relation counts, spaCy availability |
| [kg.top](../tools/kg.top.md) | introspection | read | Get top entities by mention count from the knowledge graph |
| [kg2.batch](../tools/kg2.batch.md) | memory | write | Batch extract entities from multiple unextracted memories |
| [kg2.entity](../tools/kg2.entity.md) | memory | read | Query entity graph with typed edges (KG v2 with LightNER) |
| [kg2.extract](../tools/kg2.extract.md) | memory | write | Extract entities and relations using LightNER (fast pattern-based extraction) |
| [kg2.stats](../tools/kg2.stats.md) | introspection | read | Get KG2 extraction statistics — entity/relation counts, coverage |
| [mesh.experiment.receive](../tools/mesh.experiment.receive.md) | agent | write | Receive an experiment from a peer node (called on EXPERIMENT_SHARE signal) |
| [mesh.route](../tools/mesh.route.md) | agent | read | Route an inference request to the best available mesh node |
| [mesh.route.nodes](../tools/mesh.route.nodes.md) | agent | read | Get available inference nodes, optionally filtered by model |
| [mesh.route.register](../tools/mesh.route.register.md) | agent | write | Register a mesh inference node |
| [mesh.route.status](../tools/mesh.route.status.md) | agent | read | Get inference router status (nodes, strategy, stats) |
| [oss.scan_org](../tools/oss.scan_org.md) | security | read | Scan all repos in a GitHub org for bounties |
| [oss.scan_repo](../tools/oss.scan_repo.md) | security | read | Scan a GitHub repo for bounty-labeled issues |
| [poc.generate](../tools/poc.generate.md) | security | read | Generate a PoC from a template with variables |
| [poc.verify](../tools/poc.verify.md) | security | read | Full PoC pipeline: governance → render → compile → test → verify |
| [rabbit_hole_research](../tools/rabbit_hole_research.md) | system | read | Dispatch-routable WhiteMagic tool 'rabbit_hole_research'. |
| [research_repo](../tools/research_repo.md) | system | read | Dispatch-routable WhiteMagic tool 'research_repo'. |
| [research_topic](../tools/research_topic.md) | system | read | Dispatch-routable WhiteMagic tool 'research_topic'. |
| [research_url](../tools/research_url.md) | system | read | Dispatch-routable WhiteMagic tool 'research_url'. |
| [simulation.forecast](../tools/simulation.forecast.md) | synthesis | read | Yang-within-yin: run external research simulation to model and forecast external |
| [strata.analyze](../tools/strata.analyze.md) | archaeology | read | Run STRATA static analysis on a codebase. 80+ checkers across 15 languages detec |
| [strata.archaeology](../tools/strata.archaeology.md) | archaeology | read | Git history archaeology — excavate layers, find fossils, track extinctions, anal |
| [strata.list_checks](../tools/strata.list_checks.md) | introspection | read | List all registered STRATA checkers with their descriptions and supported langua |
| [strata.survey](../tools/strata.survey.md) | archaeology | read | Fast surface survey of a codebase using file metadata and git history for quick  |
| [web_cache_clear](../tools/web_cache_clear.md) | system | read | Dispatch-routable WhiteMagic tool 'web_cache_clear'. |
| [web_cache_list](../tools/web_cache_list.md) | system | read | Dispatch-routable WhiteMagic tool 'web_cache_list'. |
| [web_fetch](../tools/web_fetch.md) | system | read | Dispatch-routable WhiteMagic tool 'web_fetch'. |
| [web_fetch_enhanced](../tools/web_fetch_enhanced.md) | system | read | Dispatch-routable WhiteMagic tool 'web_fetch_enhanced'. |
| [web_search](../tools/web_search.md) | system | read | Dispatch-routable WhiteMagic tool 'web_search'. |
| [web_search_and_read](../tools/web_search_and_read.md) | system | read | Dispatch-routable WhiteMagic tool 'web_search_and_read'. |
| [web_search_batch](../tools/web_search_batch.md) | system | read | Dispatch-routable WhiteMagic tool 'web_search_batch'. |
| [web_search_category](../tools/web_search_category.md) | system | read | Dispatch-routable WhiteMagic tool 'web_search_category'. |
| [wiki.generate](../tools/wiki.generate.md) | system | read | Dispatch-routable WhiteMagic tool 'wiki.generate'. |
| [wiki.query](../tools/wiki.query.md) | system | read | Dispatch-routable WhiteMagic tool 'wiki.query'. |
| [wiki.scan](../tools/wiki.scan.md) | system | read | Dispatch-routable WhiteMagic tool 'wiki.scan'. |
| [wiki.stats](../tools/wiki.stats.md) | system | read | Dispatch-routable WhiteMagic tool 'wiki.stats'. |
| [wiki.update](../tools/wiki.update.md) | system | read | Dispatch-routable WhiteMagic tool 'wiki.update'. |
| [windsurf.categorize](../tools/windsurf.categorize.md) | archaeology | read | Auto-categorize sessions by topic (whitemagic, ai_research, system_maintenance,  |
| [windsurf.compare](../tools/windsurf.compare.md) | archaeology | read | Compare exports across dates to find new, changed, and missing sessions. Uses ca |
| [windsurf.export_all](../tools/windsurf.export_all.md) | archaeology | write | Bulk export all Windsurf/Cascade conversations via the language server gRPC API. |
| [windsurf.full_steps](../tools/windsurf.full_steps.md) | archaeology | read | Fetch complete step-by-step data for a single session via the language server AP |
| [windsurf.ingest](../tools/windsurf.ingest.md) | archaeology | write | Parse exported Windsurf transcripts and ingest into the sessions galaxy. Classif |
| [windsurf.mine](../tools/windsurf.mine.md) | archaeology | read | Cross-session pattern mining — extracts decisions, breakthroughs, errors, topics |
| [windsurf.semantic_search](../tools/windsurf.semantic_search.md) | archaeology | read | Semantic search across all conversations using HNSW embeddings and FTS5. Searche |
| [windsurf.sync](../tools/windsurf.sync.md) | archaeology | write | Full incremental pipeline: export all sessions → compare with previous exports → |
| [windsurf_export_conversation](../tools/windsurf_export_conversation.md) | system | read | Dispatch-routable WhiteMagic tool 'windsurf_export_conversation'. |
| [windsurf_list_conversations](../tools/windsurf_list_conversations.md) | system | read | Dispatch-routable WhiteMagic tool 'windsurf_list_conversations'. |
| [windsurf_read_conversation](../tools/windsurf_read_conversation.md) | system | read | Dispatch-routable WhiteMagic tool 'windsurf_read_conversation'. |
| [windsurf_search_conversations](../tools/windsurf_search_conversations.md) | system | read | Dispatch-routable WhiteMagic tool 'windsurf_search_conversations'. |
| [windsurf_stats](../tools/windsurf_stats.md) | system | read | Dispatch-routable WhiteMagic tool 'windsurf_stats'. |
