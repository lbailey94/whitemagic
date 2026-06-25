# ruff: noqa: BLE001
"""Unified Inference CLI Commands.

Provides 'wm infer' command for local inference.
"""
import click


@click.group()
def infer():
    """Unified local inference (Wu Wei + Gan Ying)."""
    pass


@infer.command()
@click.argument('query')
@click.option('--mode', type=click.Choice(['auto', 'fast', 'explore', 'deep']),
              default='auto', help='Inference mode')
@click.option('--memory/--no-memory', default=False,
              help='Ground response in memory (RAG)')
@click.option('--json', 'json_flag', is_flag=True, help='Output as JSON')
@click.pass_context
def query(ctx, query: str, mode: str, memory: bool, json_flag: bool):
    """Run inference on a query.

    Examples:
        wm infer query "What version is WhiteMagic?"
        wm infer query "Explain quantum entanglement" --mode deep
        wm infer query "Summarize project" --memory
    """
    try:
        import json as json_lib

        from whitemagic.inference import infer as run_inference

        result = run_inference(query, mode=mode, ground_in_memory=memory)

        json_output = json_flag or ((ctx.obj or {}).get("json_output", False) if isinstance(ctx.obj, dict) else False)
        if json_output:
            output = {
                "answer": result.answer,
                "tier": result.tier,
                "confidence": result.confidence,
                "latency_ms": result.latency_ms,
                "tokens_saved": result.tokens_saved,
                "metadata": result.metadata
            }
            click.echo(json_lib.dumps(output, indent=2))
        else:
            click.echo(f"\n{result.answer}\n")
            click.echo(f"[{result.tier} tier | {result.latency_ms:.2f}ms | "
                      f"confidence: {result.confidence:.2f} | "
                      f"tokens saved: {result.tokens_saved}]")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@infer.command()
@click.option('--json', 'json_flag', is_flag=True, help='Output as JSON')
@click.pass_context
def stats(ctx, json_flag: bool):
    """Show inference statistics.

    Example:
        wm infer stats
        wm infer stats --json
    """
    try:
        import json as json_lib

        from whitemagic.inference import get_inference_stats

        stats = get_inference_stats()

        json_output = json_flag or ((ctx.obj or {}).get("json_output", False) if isinstance(ctx.obj, dict) else False)
        if json_output:
            click.echo(json_lib.dumps(stats, indent=2))
        else:
            click.echo("\n📊 Unified Inference Statistics\n")
            click.echo(f"Total queries: {stats['total_queries']}")

            tier_dist = stats.get('tier_distribution', {})
            total = stats['total_queries']
            if total > 0:
                fast = tier_dist.get('fast', 0)
                explore = tier_dist.get('explore', 0)
                deep = tier_dist.get('deep', 0)
                click.echo(f"Fast tier: {fast} ({fast/total*100:.1f}%)")
                click.echo(f"Explore tier: {explore} ({explore/total*100:.1f}%)")
                click.echo(f"Deep tier: {deep} ({deep/total*100:.1f}%)")
            else:
                click.echo("Fast tier: 0 (0.0%)")
                click.echo("Explore tier: 0 (0.0%)")
                click.echo("Deep tier: 0 (0.0%)")

            click.echo(f"Avg latency: {stats.get('average_latency_ms', 0):.2f}ms")
            click.echo(f"Total tokens saved: {stats.get('tokens_saved', 0)}")

            # Phase 3-5 stats
            if 'turbo' in stats:
                click.echo(f"\n⚡ Turbo: {stats['turbo']['model']} ({stats['turbo']['threads']} threads)")
            if 'model_pool' in stats:
                click.echo(f"🔥 Warmed models: {stats['model_pool']['warmed_models']}")
            if 'kv_cache' in stats:
                cache = stats['kv_cache']
                click.echo(f"💾 KV cache: {cache.get('hit_rate_percent', 0):.1f}% hit rate")
            if 'hardware' in stats:
                hw = stats['hardware']['current_state']
                click.echo(f"🖥️  Hardware: CPU {hw['cpu_percent']:.0f}%, Mem {hw['memory_percent']:.0f}%")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    infer()
