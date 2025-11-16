#!/usr/bin/env python3
"""
Test script to debug multi-platform collection
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('.')

async def test_multiplatform_collection():
    """Test multi-platform collection step by step"""
    print("🔍 DETAILED MULTI-PLATFORM COLLECTION TEST")
    
    from app.core.database import connect_to_mongo
    await connect_to_mongo()
    
    from app.services.cluster_service import ClusterService
    from app.collectors.x_collector import XCollector
    from app.collectors.facebook_collector import FacebookCollector
    from app.collectors.youtube_collector import YouTubeCollector
    
    # Get cluster
    cluster_service = ClusterService()
    cluster_id = "68cfafebe5dfb8a0ddba97d5"  # DMK
    cluster = await cluster_service.get_cluster(cluster_id)
    
    print(f"\n📋 Testing Cluster: {cluster.name}")
    print(f"   Keywords: {cluster.keywords}")
    
    # Test collector mapping
    collectors = {
        "x": XCollector(),
        "facebook": FacebookCollector(), 
        "youtube": YouTubeCollector()
    }
    
    print(f"\n🔧 Collectors initialized:")
    for name, collector in collectors.items():
        print(f"   {name}: {type(collector).__name__}")
    
    # Test platform config parsing
    platform_config = getattr(cluster, 'platform_config', None)
    print(f"\n⚙️ Platform Config:")
    print(f"   Type: {type(platform_config)}")
    print(f"   Config: {platform_config}")
    
    # Test each platform
    for platform_name, collector in collectors.items():
        print(f"\n--- Testing {platform_name.upper()} ---")
        
        # Get platform-specific config  
        if platform_config:
            config = getattr(platform_config, platform_name, None)
            if config and not config.enabled:
                print(f"❌ Skipping {platform_name} (disabled in configuration)")
                continue
            else:
                print(f"✅ {platform_name} enabled: {config.enabled if config else 'default'}")
        else:
            from app.models.cluster import PlatformConfig
            config = PlatformConfig()
            print(f"✅ {platform_name} using default config")
        
        try:
            # Test collection for first keyword only
            keyword = cluster.keywords[0]
            print(f"🔍 Testing search for keyword: '{keyword}'")
            
            async with collector:
                count = 0
                async for entry in collector.search(keyword, config, max_results=3):
                    count += 1
                    print(f"   Entry {count}: Found data")
                    if count >= 3:  # Limit for testing
                        break
            
            print(f"✅ {platform_name}: {count} entries found")
            
        except Exception as e:
            print(f"❌ {platform_name} Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_multiplatform_collection())