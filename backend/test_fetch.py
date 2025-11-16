#!/usr/bin/env python3
"""
Test script to verify data fetching works
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

from app.core.database import connect_to_mongo, get_database, close_mongo_connection

async def test_collections():
    """Test database collections"""
    try:
        # Connect to database
        await connect_to_mongo()
        print("✓ Connected to MongoDB")
        
        # Get database
        db = get_database()
        
        # List collections
        collections = await db.list_collection_names()
        print(f"✓ Found {len(collections)} collections: {collections}")
        
        # Check clusters
        clusters_count = await db.clusters.count_documents({})
        print(f"✓ Clusters collection has {clusters_count} documents")
        
        # Get active clusters
        active_clusters = await db.clusters.count_documents({"is_active": True})
        print(f"✓ Active clusters: {active_clusters}")
        
        # List clusters
        cursor = db.clusters.find({})
        clusters = await cursor.to_list(10)
        for cluster in clusters:
            print(f"  - {cluster.get('name', 'Unknown')}: {cluster.get('cluster_type', 'unknown')} (Active: {cluster.get('is_active', False)})")
            print(f"    Keywords: {cluster.get('keywords', [])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await close_mongo_connection()
        print("\n✓ Disconnected from MongoDB")

async def test_fetch_single_cluster():
    """Test fetching data for a single cluster"""
    try:
        await connect_to_mongo()
        db = get_database()
        
        # Get first active cluster
        cluster = await db.clusters.find_one({"is_active": True})
        if not cluster:
            print("No active clusters found. Creating a test cluster...")
            
            # Create a test cluster
            test_cluster = {
                "name": "Test Political Cluster",
                "cluster_type": "own",
                "dashboard_type": "Own",
                "keywords": ["politics", "election", "democracy"],
                "is_active": True
            }
            
            result = await db.clusters.insert_one(test_cluster)
            cluster_id = str(result.inserted_id)
            print(f"Created test cluster with ID: {cluster_id}")
        else:
            cluster_id = str(cluster["_id"])
            print(f"Using existing cluster: {cluster['name']} (ID: {cluster_id})")
        
        # Now fetch data
        from app.services.pipeline_orchestrator import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator()
        print("\nStarting data collection...")
        
        result = await orchestrator.collect_and_process_cluster(
            cluster_id=cluster_id,
            save_to_social_posts=True,
            save_to_posts_table=True
        )
        
        print(f"\n✓ Collection complete!")
        print(f"  Posts collected: {result.get('total_posts_collected', 0)}")
        print(f"  Posts processed: {result.get('total_posts_processed', 0)}")
        
        if result.get('platforms'):
            for platform, data in result['platforms'].items():
                if not isinstance(data, dict):
                    continue
                print(f"\n  {platform.upper()}:")
                print(f"    Raw collected: {data.get('raw_collected', 0)}")
                print(f"    Posts saved: {data.get('posts_saved', 0)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during fetch: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await close_mongo_connection()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test data fetching')
    parser.add_argument('--fetch', action='store_true', help='Test fetching data')
    args = parser.parse_args()
    
    if args.fetch:
        print("Testing data fetch...")
        asyncio.run(test_fetch_single_cluster())
    else:
        print("Testing database connection...")
        asyncio.run(test_collections())

if __name__ == "__main__":
    main()