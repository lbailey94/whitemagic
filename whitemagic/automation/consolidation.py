"""
Automated Memory Consolidation System

Automatically consolidates short-term memories into long-term when:
1. Short-term count > threshold (default: 40)
2. Age of memories > threshold (default: 7 days)
3. Similar/duplicate memories detected
4. On session end
5. On version release

Usage:
    from whitemagic.automation.consolidation import ConsolidationEngine
    
    manager = MemoryManager()
    engine = ConsolidationEngine(manager)
    
    # Check if consolidation needed
    check = await engine.should_consolidate()
    
    # Run auto-consolidation
    if check["should_consolidate"]:
        results = await engine.auto_consolidate(dry_run=False)
"""

import asyncio
import difflib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from whitemagic.core import MemoryManager
from whitemagic.models import Memory
from whitemagic.scratchpad.manager import ScratchpadManager
from whitemagic.parallel.pools import ThreadingTier


class ConsolidationEngine:
    """Automated memory consolidation with parallel processing"""
    
    def __init__(self, manager: MemoryManager, config: Optional[Dict] = None):
        self.manager = manager
        self.config = config or {}
        self.thresholds = {
            "count": self.config.get("max_short_term", 40),
            "age_days": self.config.get("max_age_days", 7),
            "similarity": self.config.get("similarity_threshold", 0.85)
        }
        self.scratchpad_manager = ScratchpadManager()
        
        # Parallel processing (use Tier 1: 16 threads for I/O-bound consolidation)
        self.enable_parallel = self.config.get("enable_parallel", True)
        self.worker_count = self.config.get("worker_count", ThreadingTier.TIER_1.value)
    
    def should_consolidate(self) -> Dict[str, any]:
        """Check if consolidation is needed (sync version)"""
        try:
            stats = self.manager.stats()
        except Exception:
            # Fallback if stats method doesn't exist
            short_term_count = len(list(Path(self.manager.short_term_dir).glob("*.md")))
            stats = {"short_term": short_term_count}
        
        short_term_count = stats.get("short_term", 0)
        
        reasons = []
        
        # Check count threshold
        if short_term_count > self.thresholds["count"]:
            reasons.append(f"Too many short-term memories ({short_term_count}/{self.thresholds['count']})")
        
        # Check age threshold
        old_memories = self.find_old_memories()
        if len(old_memories) > 5:
            reasons.append(f"{len(old_memories)} memories older than {self.thresholds['age_days']} days")
        
        # Check for duplicates/similar
        duplicates = self.find_duplicates()
        if len(duplicates) > 3:
            reasons.append(f"{len(duplicates)} duplicate/similar memory pairs found")
        
        return {
            "should_consolidate": len(reasons) > 0,
            "reasons": reasons,
            "count": short_term_count,
            "old_memories": len(old_memories),
            "duplicates": len(duplicates),
            "threshold": self.thresholds["count"]
        }
    
    def _archive_memory(self, memory: Memory, dry_run: bool = True) -> Dict:
        """Archive a single memory (for parallel processing)."""
        try:
            if not dry_run:
                self.manager.delete(memory.filename, permanent=False)
            return {
                "filename": memory.filename,
                "title": getattr(memory, 'title', 'Unknown'),
                "age_days": (datetime.now() - memory.created).days if hasattr(memory, 'created') else None,
                "success": True
            }
        except Exception as e:
            return {
                "filename": memory.filename,
                "success": False,
                "error": str(e)
            }
    
    def find_old_memories(self) -> List[Memory]:
        """Find memories older than age threshold"""
        cutoff_date = datetime.now() - timedelta(days=self.thresholds["age_days"])
        
        # Get all memories and filter for short-term only
        all_memories = self.manager.list_all_memories()
        short_term_files = all_memories.get("short_term", [])
        
        old = []
        for mem_data in short_term_files:
            try:
                # Parse created date from filename or metadata
                filename = mem_data.get("filename", "")
                created_str = mem_data.get("created", "")
                
                if created_str:
                    created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    if created < cutoff_date:
                        old.append(mem_data)
            except (AttributeError, TypeError, ValueError):
                # Skip if created date missing/invalid
                continue
        
        return old
    
    def find_duplicates(self) -> List[Tuple[Dict, Dict, float]]:
        """Find similar/duplicate memories by title"""
        all_memories = self.manager.list_all_memories()
        short_term_files = all_memories.get("short_term", [])
        duplicates = []
        
        # Compare all pairs
        for i, mem1 in enumerate(short_term_files):
            for mem2 in short_term_files[i+1:]:
                # Compare titles
                try:
                    title1 = mem1.get("title", "")
                    title2 = mem2.get("title", "")
                    
                    if not title1 or not title2:
                        continue
                    
                    similarity = difflib.SequenceMatcher(
                        None, title1.lower(), title2.lower()
                    ).ratio()
                    
                    if similarity > self.thresholds["similarity"]:
                        duplicates.append((mem1, mem2, similarity))
                except Exception:
                    continue
        
        # Sort by similarity (highest first)
        duplicates.sort(key=lambda x: x[2], reverse=True)
        
        return duplicates
    
    def auto_consolidate(self, dry_run: bool = True) -> Dict:
        """Automatically consolidate memories and clean scratchpads"""
        start_time = datetime.now()
        
        results = {
            "archived": [],
            "promoted": [],
            "merged": [],
            "scratchpads_cleaned": [],
            "dry_run": dry_run,
            "errors": [],
            "metrics": {
                "start_time": start_time.isoformat(),
                "parallel_enabled": self.enable_parallel,
                "worker_count": self.worker_count
            }
        }
        
        try:
            # 1. Archive old memories (parallel processing)
            old_memories = self.find_old_memories()
            
            if self.enable_parallel and len(old_memories) > 3:
                # Use parallel processing for >3 memories
                with ThreadPoolExecutor(max_workers=self.worker_count) as executor:
                    futures = {
                        executor.submit(self._archive_memory, memory, dry_run): memory 
                        for memory in old_memories
                    }
                    
                    for future in as_completed(futures):
                        result = future.result()
                        if result.get("success"):
                            results["archived"].append({
                                "filename": result["filename"],
                                "title": result["title"],
                                "age_days": result["age_days"]
                            })
                        else:
                            results["errors"].append(f"Archive failed for {result['filename']}: {result.get('error', 'Unknown')}")
            else:
                # Sequential processing for small batches
                for memory in old_memories:
                    result = self._archive_memory(memory, dry_run)
                    if result.get("success"):
                        results["archived"].append({
                            "filename": result["filename"],
                            "title": result["title"],
                            "age_days": result["age_days"]
                        })
                    else:
                        results["errors"].append(f"Archive failed for {result['filename']}: {result.get('error', 'Unknown')}")
            
            # 2. Merge highly similar duplicates (top 5)
            duplicates = self.find_duplicates()[:5]
            for mem1, mem2, similarity in duplicates:
                try:
                    if not dry_run:
                        # Create merged long-term memory
                        merged_content = f"# Consolidated Memory\n\n"
                        merged_content += f"**Combined from**: {mem1.filename}, {mem2.filename}\n"
                        merged_content += f"**Similarity**: {similarity:.1%}\n\n"
                        merged_content += f"## {mem1.title if hasattr(mem1, 'title') else 'Memory 1'}\n\n"
                        merged_content += f"{mem1.content}\n\n---\n\n"
                        merged_content += f"## {mem2.title if hasattr(mem2, 'title') else 'Memory 2'}\n\n"
                        merged_content += f"{mem2.content}\n\n"
                        
                        # Combine tags
                        tags1 = mem1.tags if hasattr(mem1, 'tags') else []
                        tags2 = mem2.tags if hasattr(mem2, 'tags') else []
                        merged_tags = list(set(tags1 + tags2 + ["consolidated"]))
                        
                        merged = self.manager.create_memory(
                            title=f"Consolidated: {mem1.title if hasattr(mem1, 'title') else 'Memories'}",
                            content=merged_content,
                            type="long_term",
                            tags=merged_tags
                        )
                        
                        # Archive originals
                        self.manager.delete(mem1.filename, permanent=False)
                        self.manager.delete(mem2.filename, permanent=False)
                        
                        results["merged"].append({
                            "source1": mem1.filename,
                            "source2": mem2.filename,
                            "target": merged.filename,
                            "similarity": f"{similarity:.1%}"
                        })
                    else:
                        results["merged"].append({
                            "source1": mem1.filename,
                            "source2": mem2.filename,
                            "similarity": f"{similarity:.1%}",
                            "note": "Would be merged"
                        })
                except Exception as e:
                    results["errors"].append(f"Merge failed for {mem1.filename} + {mem2.filename}: {str(e)}")
            
            # 3. Auto-promote memories (enhanced logic)
            all_mem = self.manager.list_all_memories()
            short_term_files = all_mem.get("short_term", [])
            important_tags = ["critical", "important", "permanent", "reference", "keep"]
            
            for mem_data in short_term_files:
                try:
                    memory_tags = mem_data.get('tags', [])
                    content = mem_data.get('content', '')
                    created_str = mem_data.get('created')
                    
                    # Calculate promotion score
                    should_promote = False
                    promotion_reason = []
                    
                    # Rule 1: Tag-based promotion
                    if any(tag.lower() in important_tags for tag in memory_tags):
                        should_promote = True
                        promotion_reason.append("important_tags")
                    
                    # Rule 2: Age-based promotion (>30 days)
                    if created_str:
                        try:
                            created = datetime.fromisoformat(created_str.replace('Z', ''))
                            age_days = (datetime.now() - created).days
                            if age_days > 30:
                                should_promote = True
                                promotion_reason.append(f"age_{age_days}d")
                        except Exception:
                            pass
                    
                    # Rule 3: Size-based promotion (>1000 words)
                    word_count = len(content.split())
                    if word_count > 1000:
                        should_promote = True
                        promotion_reason.append(f"size_{word_count}w")
                    
                    # Rule 4: Title indicators (comprehensive, guide, reference)
                    title = mem_data.get('title', '').lower()
                    if any(keyword in title for keyword in ['comprehensive', 'guide', 'reference', 'complete', 'roadmap']):
                        should_promote = True
                        promotion_reason.append("comprehensive_doc")
                    
                    if should_promote:
                        if not dry_run:
                            # Promote to long-term
                            promoted = self.manager.create_memory(
                                title=mem_data.get('title', "Promoted Memory"),
                                content=content,
                                type="long_term",
                                tags=memory_tags + ["auto_promoted"]
                            )
                            self.manager.delete(mem_data.get('filename'), permanent=False)
                            
                            results["promoted"].append({
                                "source": mem_data.get('filename'),
                                "target": promoted.filename,
                                "reason": ", ".join(promotion_reason),
                                "tags": memory_tags
                            })
                        else:
                            results["promoted"].append({
                                "source": mem_data.get('filename'),
                                "reason": ", ".join(promotion_reason),
                                "tags": memory_tags,
                                "note": "Would be promoted"
                            })
                except Exception as e:
                    results["errors"].append(f"Promotion failed for {mem_data.get('filename', 'unknown')}: {str(e)}")
            
            # 4. Clean old scratchpads (>24 hours)
            try:
                # Create event loop if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                scratchpad_results = loop.run_until_complete(
                    self.scratchpad_manager.cleanup_old(hours=24, dry_run=dry_run)
                )
                results["scratchpads_cleaned"] = scratchpad_results.get("cleaned", [])
            except Exception as e:
                results["errors"].append(f"Scratchpad cleanup failed: {str(e)}")
        
        except Exception as e:
            results["errors"].append(f"Consolidation failed: {str(e)}")
        
        # Add completion metrics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        results["metrics"].update({
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_actions": (
                len(results["archived"]) + 
                len(results["promoted"]) + 
                len(results["merged"]) + 
                len(results["scratchpads_cleaned"])
            ),
            "success": len(results["errors"]) == 0
        })
        
        return results
    
    def consolidate_session(self, session_id: str, dry_run: bool = True) -> Optional[Memory]:
        """Create session consolidation memory"""
        try:
            # Get all memories from session
            memories = self.manager.search_memories(tags=[f"session_{session_id}"])
            
            if not memories:
                return None
            
            # Create consolidated summary
            content = f"# Session {session_id} Summary\n\n"
            content += f"**Date**: {datetime.now().isoformat()}\n"
            content += f"**Memories Consolidated**: {len(memories)}\n\n"
            content += "## Contents\n\n"
            
            for memory in memories:
                title = memory.title if hasattr(memory, 'title') else "Untitled"
                tags = memory.tags if hasattr(memory, 'tags') else []
                content_preview = memory.content[:300] if hasattr(memory, 'content') else ""
                
                content += f"### {title}\n\n"
                content += f"**Tags**: {', '.join(tags)}\n\n"
                content += f"{content_preview}...\n\n---\n\n"
            
            if not dry_run:
                # Create long-term consolidation memory
                consolidated = self.manager.create_memory(
                    title=f"Session {session_id} - Consolidated",
                    content=content,
                    type="long_term",
                    tags=["consolidation", "session", session_id]
                )
                
                # Archive original memories
                for memory in memories:
                    try:
                        self.manager.delete(memory.filename, permanent=False)
                    except Exception:
                        pass
                
                return consolidated
            else:
                return None
        
        except Exception as e:
            print(f"Session consolidation failed: {e}")
            return None


def consolidate_cli(args):
    """CLI command for consolidation (sync wrapper)"""
    from whitemagic.core import MemoryManager
    
    manager = MemoryManager()
    engine = ConsolidationEngine(manager)
    
    # Check if needed
    check = engine.should_consolidate()
    
    if not check["should_consolidate"]:
        print("✓ No consolidation needed")
        print(f"  Short-term memories: {check['count']}/{check['threshold']}")
        return
    
    print("📊 Consolidation Analysis:")
    print(f"  Short-term count: {check['count']}/{check['threshold']}")
    for reason in check["reasons"]:
        print(f"  • {reason}")
    
    # Run consolidation
    dry_run = not args.no_dry_run
    
    if dry_run:
        print("\n🔍 DRY RUN (use --no-dry-run to execute)")
    else:
        print("\n🔄 Running consolidation...")
    
    results = engine.auto_consolidate(dry_run=dry_run)
    
    print(f"\n{'Would be' if dry_run else 'Consolidation'} Results:")
    if results["archived"]:
        print(f"  📦 Archived: {len(results['archived'])} memories")
        for item in results["archived"][:5]:
            print(f"     - {item['filename']} ({item.get('age_days', '?')} days old)")
        if len(results["archived"]) > 5:
            print(f"     ... and {len(results['archived']) - 5} more")
    
    if results["merged"]:
        print(f"  🔗 Merged: {len(results['merged'])} memory pairs")
        for item in results["merged"][:3]:
            print(f"     - {item['source1']} + {item['source2']} ({item['similarity']})")
        if len(results["merged"]) > 3:
            print(f"     ... and {len(results['merged']) - 3} more")
    
    if results["promoted"]:
        print(f"  ⬆️  Promoted: {len(results['promoted'])} memories to long-term")
        for item in results["promoted"][:3]:
            reason = item.get('reason', 'N/A')
            print(f"     - {item['source']} ({reason})")
        if len(results["promoted"]) > 3:
            print(f"     ... and {len(results['promoted']) - 3} more")
    
    if results["scratchpads_cleaned"]:
        print(f"  🧹 Scratchpads: {len(results['scratchpads_cleaned'])} cleaned (>24h old)")
        for item in results["scratchpads_cleaned"][:3]:
            age_hours = item.get('age_hours', 0)
            print(f"     - {item['name']} ({age_hours:.1f}h old)")
        if len(results["scratchpads_cleaned"]) > 3:
            print(f"     ... and {len(results['scratchpads_cleaned']) - 3} more")
    
    if results["errors"]:
        print(f"\n⚠️  Errors: {len(results['errors'])}")
        for error in results["errors"][:3]:
            print(f"     - {error}")
    
    if dry_run:
        print("\n💡 Run with --no-dry-run to execute consolidation")
    else:
        print("\n✅ Consolidation complete!")
