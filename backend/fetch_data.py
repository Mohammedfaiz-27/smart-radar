#!/usr/bin/env python3
"""
Script to fetch data from social media platforms and store in database
Can be run manually or scheduled via cron/scheduler
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / '.env')

from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.core.database import connect_to_mongo, close_mongo_connection

async def fetch_data_for_cluster(cluster_id: str = None):
    """
    Fetch data for a specific cluster or all active clusters
    
    Args:
        cluster_id: Optional cluster ID to fetch data for
    """
    try:
        # Connect to database
        await connect_to_mongo()
        print("Connected to MongoDB")
        
        # Initialize orchestrator
        orchestrator = PipelineOrchestrator()
        
        if cluster_id:
            # Fetch for specific cluster
            print(f"Fetching data for cluster: {cluster_id}")
            result = await orchestrator.collect_and_process_cluster(
                cluster_id=cluster_id,
                save_to_social_posts=True,  # Save to social_posts for backward compatibility
                save_to_posts_table=True     # Save to new posts_table
            )
        else:
            # Fetch for all active clusters
            print("Fetching data for all active clusters")
            result = await orchestrator.collect_all_active_clusters()
        
        # Print results
        print("\n" + "="*60)
        print("FETCH COMPLETE")
        print("="*60)
        
        if cluster_id:
            print(f"Cluster: {result.get('cluster_name', 'Unknown')}")
            print(f"Posts collected: {result.get('total_posts_collected', 0)}")
            print(f"Posts processed: {result.get('total_posts_processed', 0)}")
            
            if result.get('platforms'):
                print("\nPlatform breakdown:")
                for platform, data in result['platforms'].items():
                    print(f"  {platform.upper()}:")
                    print(f"    - Raw collected: {data.get('raw_collected', 0)}")
                    print(f"    - Posts saved: {data.get('posts_saved', 0)}")
        else:
            print(f"Clusters processed: {result.get('clusters_processed', 0)}")
            print(f"Total posts collected: {result.get('total_posts_collected', 0)}")
            print(f"Total posts processed: {result.get('total_posts_processed', 0)}")
        
        if result.get('errors'):
            print(f"\nErrors encountered: {len(result['errors'])}")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        return result
        
    except Exception as e:
        print(f"Error during data fetch: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
    finally:
        # Close database connection
        await close_mongo_connection()
        print("\nDisconnected from MongoDB")

async def process_pending_data():
    """Process any pending raw data"""
    try:
        await connect_to_mongo()
        print("Processing pending raw data...")
        
        orchestrator = PipelineOrchestrator()
        result = await orchestrator.process_pending_raw_data(limit=100)
        
        print(f"Processed {result.get('entries_processed', 0)} entries")
        print(f"Created {result.get('posts_created', 0)} posts")
        
        return result
        
    except Exception as e:
        print(f"Error processing pending data: {e}")
        return {"error": str(e)}
    
    finally:
        await close_mongo_connection()

async def get_status():
    """Get current collection status"""
    try:
        await connect_to_mongo()
        
        orchestrator = PipelineOrchestrator()
        status = await orchestrator.get_collection_status()
        
        print("\n" + "="*60)
        print("COLLECTION STATUS")
        print("="*60)
        
        print(f"\nClusters:")
        print(f"  Total: {status['clusters']['total']}")
        print(f"  Active: {status['clusters']['active']}")
        
        print(f"\nRaw Data:")
        print(f"  Total records: {status['raw_data']['total_records']}")
        print(f"  Pending: {status['raw_data']['pending_processing']}")
        print(f"  Failed: {status['raw_data']['failed_processing']}")
        print(f"  Size: {status['raw_data']['size_mb']} MB")
        
        print(f"\nPosts:")
        print(f"  Total: {status['posts']['total']}")
        print(f"  Threats: {status['posts']['threats']}")
        
        if status['posts']['by_platform']:
            print(f"\n  By Platform:")
            for platform, count in status['posts']['by_platform'].items():
                print(f"    {platform}: {count}")
        
        if status['posts']['by_sentiment']:
            print(f"\n  By Sentiment:")
            for sentiment, count in status['posts']['by_sentiment'].items():
                print(f"    {sentiment}: {count}")
        
        return status
        
    except Exception as e:
        print(f"Error getting status: {e}")
        return {"error": str(e)}
    
    finally:
        await close_mongo_connection()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch social media data')
    parser.add_argument(
        '--cluster-id',
        help='Specific cluster ID to fetch data for'
    )
    parser.add_argument(
        '--process-pending',
        action='store_true',
        help='Process pending raw data'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show collection status'
    )
    
    args = parser.parse_args()
    
    if args.status:
        # Show status
        asyncio.run(get_status())
    elif args.process_pending:
        # Process pending data
        asyncio.run(process_pending_data())
    else:
        # Fetch new data
        asyncio.run(fetch_data_for_cluster(args.cluster_id))

if __name__ == "__main__":
    main()