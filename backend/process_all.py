#!/usr/bin/env python3
"""Process ALL raw_data entries"""
import asyncio
from app.services.pipeline_orchestrator import PipelineOrchestrator

async def main():
    print("Processing ALL raw_data entries...")

    orchestrator = PipelineOrchestrator()

    # Process in batches
    total_processed = 0
    total_saved = 0

    while True:
        result = await orchestrator.process_pending_raw_data(limit=50)

        processed = result.get('processed', 0)
        saved = result.get('saved', 0)

        total_processed += processed
        total_saved += saved

        print(f"Batch complete: {processed} processed, {saved} saved (Total: {total_processed}/{total_saved})")

        if processed == 0:
            break

    print(f"\n✓ All processing complete!")
    print(f"  Total processed: {total_processed}")
    print(f"  Total saved to posts_table: {total_saved}")

if __name__ == '__main__':
    asyncio.run(main())
