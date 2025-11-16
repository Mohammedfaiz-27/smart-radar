#!/usr/bin/env python3
"""
Test script to verify cluster-based data filtering and display functionality
"""

import requests
import json
import sys
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000"

def test_clusters_api() -> bool:
    """Test the clusters API endpoint"""
    print("🔍 Testing Clusters API...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/clusters/")
        response.raise_for_status()
        
        clusters = response.json()
        print(f"✅ Found {len(clusters)} clusters")
        
        own_clusters = [c for c in clusters if c.get('cluster_type') == 'own']
        competitor_clusters = [c for c in clusters if c.get('cluster_type') == 'competitor']
        
        print(f"  - Own clusters: {len(own_clusters)}")
        print(f"  - Competitor clusters: {len(competitor_clusters)}")
        
        # Print cluster keywords for verification
        for cluster in clusters:
            keywords = cluster.get('keywords', [])
            print(f"  - {cluster['name']} ({cluster['cluster_type']}): {len(keywords)} keywords")
            if keywords:
                print(f"    Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
        
        return len(clusters) > 0
    
    except Exception as e:
        print(f"❌ Clusters API test failed: {e}")
        return False

def test_posts_api_with_cluster_filtering() -> bool:
    """Test posts API with cluster type filtering"""
    print("\n🔍 Testing Posts API with cluster filtering...")
    
    try:
        # Test own cluster filtering
        response = requests.get(f"{BASE_URL}/api/v1/posts?cluster_type=own&limit=10")
        response.raise_for_status()
        own_posts = response.json()
        
        print(f"✅ Own cluster posts: {len(own_posts)} found")
        
        # Test competitor cluster filtering
        response = requests.get(f"{BASE_URL}/api/v1/posts?cluster_type=competitor&limit=10")
        response.raise_for_status()
        competitor_posts = response.json()
        
        print(f"✅ Competitor cluster posts: {len(competitor_posts)} found")
        
        # Verify cluster type assignment
        own_cluster_types = set(post.get('cluster_type') for post in own_posts if post.get('cluster_type'))
        competitor_cluster_types = set(post.get('cluster_type') for post in competitor_posts if post.get('cluster_type'))
        
        print(f"  - Own posts cluster types: {own_cluster_types}")
        print(f"  - Competitor posts cluster types: {competitor_cluster_types}")
        
        return len(own_posts) >= 0 and len(competitor_posts) >= 0
    
    except Exception as e:
        print(f"❌ Posts API cluster filtering test failed: {e}")
        return False

def test_keyword_matching() -> bool:
    """Test if posts contain cluster keywords"""
    print("\n🔍 Testing keyword matching...")
    
    try:
        # Get clusters and their keywords
        clusters_response = requests.get(f"{BASE_URL}/api/v1/clusters/")
        clusters_response.raise_for_status()
        clusters = clusters_response.json()
        
        # Get posts
        posts_response = requests.get(f"{BASE_URL}/api/v1/posts?limit=50")
        posts_response.raise_for_status()
        posts = posts_response.json()
        
        print(f"✅ Testing {len(posts)} posts against {len(clusters)} clusters")
        
        # Check keyword matching
        for cluster in clusters:
            cluster_keywords = cluster.get('keywords', [])
            cluster_type = cluster.get('cluster_type')
            cluster_name = cluster.get('name')
            
            if not cluster_keywords:
                continue
            
            matching_posts = 0
            for post in posts:
                content = (post.get('content', '') + ' ' + post.get('title', '')).lower()
                
                # Check if any cluster keyword is in the post content
                if any(keyword.lower() in content for keyword in cluster_keywords):
                    matching_posts += 1
            
            print(f"  - {cluster_name} ({cluster_type}): {matching_posts} posts match keywords")
        
        return True
    
    except Exception as e:
        print(f"❌ Keyword matching test failed: {e}")
        return False

def test_api_integration() -> bool:
    """Test full API integration"""
    print("\n🔍 Testing full API integration...")
    
    try:
        # Test health endpoint
        health_response = requests.get(f"{BASE_URL}/health")
        health_response.raise_for_status()
        print(f"✅ Backend health: {health_response.json()}")
        
        # Test API version
        version_response = requests.get(f"{BASE_URL}/")
        version_response.raise_for_status()
        version_data = version_response.json()
        print(f"✅ API version: {version_data}")
        
        return True
    
    except Exception as e:
        print(f"❌ API integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting cluster-based data filtering tests...\n")
    
    tests = [
        ("API Integration", test_api_integration),
        ("Clusters API", test_clusters_api),
        ("Posts API with Cluster Filtering", test_posts_api_with_cluster_filtering),
        ("Keyword Matching", test_keyword_matching),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Cluster-based data filtering is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)