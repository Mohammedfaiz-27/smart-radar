# Multi-Entity Aspect-Based Sentiment Analysis Implementation Guide

## 📋 Implementation Status

### ✅ COMPLETED (Phase 1)
- [x] Updated `posts_table.py` schema with `entity_sentiments` and `comparative_analysis` fields
- [x] Created comprehensive multi-entity LLM prompt in `llm_processing_service.py`
- [x] Implemented `analyze_post_multi_entity()` method with fallback logic
- [x] Configured for Tamil Nadu politics: DMK (own) vs ADMK/BJP/TVK (competitors)

### 🔄 IN PROGRESS
- [ ] Update PipelineOrchestrator to use multi-entity analysis
- [ ] Create API endpoints for entity-based queries
- [ ] Create migration script for existing data
- [ ] Update frontend components

---

## 🎯 System Configuration

### Political Entities Tracked
- **Own Cluster:** DMK
- **Competitor Clusters:** ADMK, BJP, TVK

### Analysis Rules Implemented
1. ✅ Emoji at end with no target → Apply to ALL mentioned entities
2. ✅ Comparative statements: "X better than Y" → X=positive, Y=negative
3. ✅ Unmentioned entities → Omit from `entity_sentiments` (no null/0.0)
4. ✅ Pronoun resolution: "BJP failed. Their..." → "Their" refers to BJP
5. ✅ Sarcasm detection → Flip sentiment score

---

## 📊 Database Schema Updates

### posts_table Collection

**NEW FIELDS:**
```python
# posts_table.py:90-120
entity_sentiments: Optional[Dict[str, Dict[str, Any]]] = Field(
    default_factory=dict,
    description="Entity-specific sentiment analysis"
)
# Structure:
{
    "DMK": {
        "label": "Positive",
        "score": 0.75,
        "confidence": 0.85,
        "mentioned_count": 3,
        "context_relevance": 0.9,
        "text_sentiment": {"score": 0.8, "segments": [...]},
        "emoji_sentiment": {"score": 0.7, "emojis": [...]},
        "hashtag_sentiment": {"score": 0.6, "hashtags": [...]},
        "sarcasm_detected": false,
        "threat_level": 0.0,
        "threat_reasoning": "..."
    }
}

comparative_analysis: Optional[Dict[str, Any]] = Field(
    default=None,
    description="Entity relationships when multiple mentioned"
)
# Structure:
{
    "has_comparison": true,
    "comparison_type": "Direct Contrast",
    "entities_compared": ["DMK", "BJP"],
    "relationship": "DMK praised while BJP criticized",
    "context_segments": ["relevant text"]
}
```

**LEGACY FIELDS (maintained for backward compatibility):**
- `sentiment_score` - Calculated as average of all entity scores
- `sentiment_label` - Derived from average score

---

## 🧠 LLM Processing Service Updates

### New Methods Added

**File:** `/backend/app/services/llm_processing_service.py`

#### 1. `create_multi_entity_analysis_prompt()` (Lines 533-750)
Creates comprehensive prompt with:
- Entity detection for DMK/ADMK/BJP/TVK
- Per-entity sentiment breakdown (text 50%, emoji 30%, hashtag 20%)
- Comparative analysis logic
- Sarcasm detection rules
- Pronoun resolution
- Threat assessment per entity

#### 2. `analyze_post_multi_entity()` (Lines 752-801)
Main analysis method:
```python
async def analyze_post_multi_entity(
    post_text: str,
    platform: str,
    author: str,
    active_clusters: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Returns:
    {
        "detected_entities": ["DMK", "BJP"],
        "entity_sentiments": {...},
        "comparative_analysis": {...},
        "overall_analysis": {...}
    }
    """
```

#### 3. `_parse_multi_entity_response()` (Lines 803-826)
Parses JSON from LLM with error handling

#### 4. `_create_basic_entity_analysis()` (Lines 828-888)
Fallback when LLM unavailable - uses keyword matching

---

## 🔄 NEXT STEPS: Pipeline Integration

### Step 1: Update PipelineOrchestrator

**File:** `/backend/app/services/pipeline_orchestrator.py`

**Current:** Lines ~160-180 call single-sentiment `process_post()`
**Update:** Call `analyze_post_multi_entity()` instead

```python
# FIND: Around line 160-180 in collect_and_process_cluster()
# OLD CODE:
update = await llm_service.process_post(post_create)

# REPLACE WITH:
# Get all active clusters for entity detection
active_clusters = await self.cluster_service.get_clusters(is_active=True)
cluster_data = [
    {
        "name": c.name,
        "keywords": c.keywords,
        "cluster_type": c.cluster_type
    }
    for c in active_clusters
]

# Perform multi-entity analysis
entity_analysis = await llm_service.analyze_post_multi_entity(
    post_text=post_create.post_text,
    platform=post_create.platform.value,
    author=post_create.author_username,
    active_clusters=cluster_data
)

# Extract data
entity_sentiments = entity_analysis.get("entity_sentiments", {})
comparative = entity_analysis.get("comparative_analysis", {})
overall = entity_analysis.get("overall_analysis", {})

# Update post with entity data
post_create.entity_sentiments = entity_sentiments
post_create.comparative_analysis = comparative

# Calculate legacy fields for backward compatibility
post_create.sentiment_score = _calculate_overall_sentiment(entity_sentiments)
post_create.sentiment_label = _determine_overall_label(entity_sentiments)
post_create.is_threat = overall.get("overall_threat_score", 0.0) > 0.5
post_create.threat_level = overall.get("overall_threat_level", "None")
post_create.language = overall.get("language", "Unknown")
```

**ADD HELPER FUNCTIONS** (add to PipelineOrchestrator class):
```python
def _calculate_overall_sentiment(self, entity_sentiments: Dict) -> float:
    """Calculate overall sentiment from entity scores"""
    if not entity_sentiments:
        return 0.0

    scores = [e.get("score", 0.0) for e in entity_sentiments.values()]
    return sum(scores) / len(scores) if scores else 0.0

def _determine_overall_label(self, entity_sentiments: Dict) -> SentimentLabel:
    """Determine overall label from entity sentiments"""
    avg_score = self._calculate_overall_sentiment(entity_sentiments)

    if avg_score >= 0.3:
        return SentimentLabel.POSITIVE
    elif avg_score <= -0.3:
        return SentimentLabel.NEGATIVE
    else:
        return SentimentLabel.NEUTRAL
```

---

## 🌐 API Endpoints to Create

### File: `/backend/app/api/entity_analytics.py` (NEW FILE)

```python
"""
Entity-based analytics and query endpoints
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.core.database import get_database

router = APIRouter()

@router.get("/posts/by-entity-sentiment")
async def get_posts_by_entity_sentiment(
    entity_name: str = Query(..., description="Entity name (DMK/ADMK/BJP/TVK)"),
    sentiment: Optional[str] = Query(None, regex="^(Positive|Negative|Neutral)$"),
    min_score: Optional[float] = Query(None, ge=-1.0, le=1.0),
    max_score: Optional[float] = Query(None, ge=-1.0, le=1.0),
    platform: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0)
):
    """
    Get posts filtered by entity-specific sentiment

    Examples:
    - /entity/posts/by-entity-sentiment?entity_name=DMK&sentiment=Positive
    - /entity/posts/by-entity-sentiment?entity_name=BJP&min_score=-1.0&max_score=-0.5
    """
    db = get_database()
    posts_collection = db.posts_table

    # Build query
    query = {
        f"entity_sentiments.{entity_name}": {"$exists": True}
    }

    if sentiment:
        query[f"entity_sentiments.{entity_name}.label"] = sentiment

    if min_score is not None or max_score is not None:
        score_query = {}
        if min_score is not None:
            score_query["$gte"] = min_score
        if max_score is not None:
            score_query["$lte"] = max_score
        query[f"entity_sentiments.{entity_name}.score"] = score_query

    if platform:
        query["platform"] = platform

    # Execute query
    cursor = posts_collection.find(query).sort("posted_at", -1).skip(skip).limit(limit)
    posts = await cursor.to_list(length=limit)

    # Format response
    return {
        "entity": entity_name,
        "filters": {"sentiment": sentiment, "min_score": min_score, "max_score": max_score},
        "total": await posts_collection.count_documents(query),
        "posts": posts
    }

@router.get("/analytics/entity/{entity_name}")
async def get_entity_analytics(entity_name: str):
    """
    Get comprehensive analytics for a specific entity

    Returns:
    - Total mentions
    - Sentiment distribution
    - Average sentiment score
    - Platform breakdown
    - Trend over time
    """
    db = get_database()
    posts_collection = db.posts_table

    # Aggregation pipeline
    pipeline = [
        # Match posts mentioning this entity
        {"$match": {f"entity_sentiments.{entity_name}": {"$exists": True}}},

        # Project entity sentiment
        {"$project": {
            "entity_score": f"$entity_sentiments.{entity_name}.score",
            "entity_label": f"$entity_sentiments.{entity_name}.label",
            "platform": 1,
            "posted_at": 1
        }},

        # Group and calculate stats
        {"$facet": {
            "total_mentions": [{"$count": "count"}],

            "sentiment_distribution": [
                {"$group": {
                    "_id": "$entity_label",
                    "count": {"$sum": 1}
                }}
            ],

            "average_sentiment": [
                {"$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$entity_score"},
                    "min_score": {"$min": "$entity_score"},
                    "max_score": {"$max": "$entity_score"}
                }}
            ],

            "platform_breakdown": [
                {"$group": {
                    "_id": "$platform",
                    "count": {"$sum": 1},
                    "avg_sentiment": {"$avg": "$entity_score"}
                }}
            ]
        }}
    ]

    result = await posts_collection.aggregate(pipeline).to_list(1)

    if not result:
        raise HTTPException(status_code=404, detail=f"No data found for entity: {entity_name}")

    return {
        "entity": entity_name,
        "analytics": result[0]
    }

@router.get("/comparative-posts")
async def get_comparative_posts(
    entity1: str = Query(..., description="First entity"),
    entity2: str = Query(..., description="Second entity"),
    comparison_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get posts that compare two entities

    Examples:
    - /entity/comparative-posts?entity1=DMK&entity2=BJP
    - /entity/comparative-posts?entity1=DMK&entity2=BJP&comparison_type=Direct Contrast
    """
    db = get_database()
    posts_collection = db.posts_table

    # Build query for posts mentioning both entities with comparison
    query = {
        f"entity_sentiments.{entity1}": {"$exists": True},
        f"entity_sentiments.{entity2}": {"$exists": True},
        "comparative_analysis.has_comparison": True
    }

    if comparison_type:
        query["comparative_analysis.comparison_type"] = comparison_type

    # Execute
    cursor = posts_collection.find(query).sort("posted_at", -1).limit(limit)
    posts = await cursor.to_list(length=limit)

    return {
        "entities_compared": [entity1, entity2],
        "comparison_type": comparison_type,
        "total": len(posts),
        "posts": posts
    }

@router.get("/entity-comparison-matrix")
async def get_entity_comparison_matrix():
    """
    Get sentiment correlation matrix for all entities

    Shows when Entity A is positive, what's Entity B's sentiment?
    """
    db = get_database()
    posts_collection = db.posts_table

    entities = ["DMK", "ADMK", "BJP", "TVK"]
    matrix = {}

    for entity_a in entities:
        matrix[entity_a] = {}
        for entity_b in entities:
            if entity_a == entity_b:
                matrix[entity_a][entity_b] = {"correlation": 1.0, "count": 0}
                continue

            # Find posts mentioning both
            pipeline = [
                {"$match": {
                    f"entity_sentiments.{entity_a}": {"$exists": True},
                    f"entity_sentiments.{entity_b}": {"$exists": True}
                }},
                {"$project": {
                    "score_a": f"$entity_sentiments.{entity_a}.score",
                    "score_b": f"$entity_sentiments.{entity_b}.score"
                }},
                {"$group": {
                    "_id": None,
                    "correlation": {
                        "$avg": {
                            "$multiply": ["$score_a", "$score_b"]
                        }
                    },
                    "count": {"$sum": 1}
                }}
            ]

            result = await posts_collection.aggregate(pipeline).to_list(1)

            if result:
                matrix[entity_a][entity_b] = result[0]
            else:
                matrix[entity_a][entity_b] = {"correlation": 0.0, "count": 0}

    return {
        "entities": entities,
        "correlation_matrix": matrix
    }
```

**ADD TO MAIN.PY:**
```python
from app.api.entity_analytics import router as entity_analytics_router

app.include_router(entity_analytics_router, prefix="/api/v1/entity", tags=["entity-analytics"])
```

---

## 🔄 Migration Script

### File: `/backend/scripts/migrate_to_entity_sentiments.py` (NEW)

```python
"""
Migration script: Convert existing single-sentiment posts to entity-based sentiment

Usage:
    cd backend
    uv run python scripts/migrate_to_entity_sentiments.py
"""
import asyncio
from datetime import datetime
from app.core.database import connect_to_mongo, get_database

async def migrate_posts_to_entity_sentiment():
    """
    Migrate existing posts from single sentiment to entity-based

    Strategy:
    1. Find posts with sentiment_score but no entity_sentiments
    2. Map cluster_id to cluster name
    3. Create entity_sentiments entry for that cluster
    4. Calculate legacy fields from entity_sentiments
    """
    await connect_to_mongo()
    db = get_database()

    posts_collection = db.posts_table
    clusters_collection = db.clusters

    print("="*80)
    print("MIGRATION: Single Sentiment → Multi-Entity Sentiment")
    print("="*80)

    # Build cluster ID → name mapping
    clusters = await clusters_collection.find().to_list(None)
    cluster_map = {str(c["_id"]): c["name"] for c in clusters}

    print(f"\n📊 Found {len(clusters)} clusters:")
    for cid, name in cluster_map.items():
        print(f"  - {name} (ID: {cid})")

    # Find posts to migrate
    query = {
        "$or": [
            {"entity_sentiments": {"$exists": False}},
            {"entity_sentiments": {}}  # Empty dict
        ],
        "sentiment_score": {"$exists": True}
    }

    total_posts = await posts_collection.count_documents(query)
    print(f"\n📝 Found {total_posts} posts to migrate")

    if total_posts == 0:
        print("✅ No posts need migration!")
        return

    # Migrate in batches
    batch_size = 100
    migrated_count = 0
    error_count = 0

    cursor = posts_collection.find(query)

    async for post in cursor:
        try:
            cluster_id = str(post.get("cluster_id", ""))
            cluster_name = cluster_map.get(cluster_id)

            if not cluster_name:
                print(f"⚠️  Post {post['_id']} has invalid cluster_id: {cluster_id}")
                error_count += 1
                continue

            # Create entity sentiment from legacy fields
            entity_sentiments = {
                cluster_name: {
                    "label": post.get("sentiment_label", "Neutral"),
                    "score": post.get("sentiment_score", 0.0),
                    "confidence": 0.6,  # Migrated data has lower confidence
                    "mentioned_count": 1,
                    "context_relevance": 1.0,
                    "text_sentiment": {
                        "score": post.get("sentiment_score", 0.0),
                        "segments": []  # No segmentation data from legacy
                    },
                    "emoji_sentiment": {
                        "score": 0.0,
                        "emojis": [],
                        "assignment_reason": "migrated from legacy"
                    },
                    "hashtag_sentiment": {
                        "score": 0.0,
                        "hashtags": []
                    },
                    "sarcasm_detected": False,
                    "sarcasm_reasoning": "",
                    "threat_level": 1.0 if post.get("is_threat") else 0.0,
                    "threat_reasoning": post.get("threat_level", "None")
                }
            }

            # No comparative analysis for single-entity posts
            comparative_analysis = {
                "has_comparison": False,
                "comparison_type": "None",
                "entities_compared": [],
                "relationship": "",
                "context_segments": []
            }

            # Update post
            await posts_collection.update_one(
                {"_id": post["_id"]},
                {
                    "$set": {
                        "entity_sentiments": entity_sentiments,
                        "comparative_analysis": comparative_analysis,
                        "migrated_to_entity_sentiment": True,
                        "migration_date": datetime.utcnow()
                    }
                }
            )

            migrated_count += 1

            if migrated_count % 100 == 0:
                print(f"  Migrated {migrated_count}/{total_posts} posts...")

        except Exception as e:
            print(f"❌ Error migrating post {post.get('_id')}: {e}")
            error_count += 1
            continue

    print("\n" + "="*80)
    print("MIGRATION COMPLETE")
    print("="*80)
    print(f"✅ Successfully migrated: {migrated_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total processed: {migrated_count + error_count}")

    return {
        "status": "success",
        "migrated_count": migrated_count,
        "error_count": error_count
    }

if __name__ == "__main__":
    asyncio.run(migrate_posts_to_entity_sentiment())
```

**RUN MIGRATION:**
```bash
cd backend
uv run python scripts/migrate_to_entity_sentiments.py
```

---

## 🎨 Frontend Updates

### Step 1: TypeScript Types

**File:** `/frontend/src/types/posts.ts` (CREATE NEW FILE)

```typescript
export interface EntitySentiment {
  label: 'Positive' | 'Negative' | 'Neutral'
  score: number  // -1.0 to 1.0
  confidence: number  // 0.0 to 1.0
  mentioned_count: number
  context_relevance: number

  text_sentiment?: {
    score: number
    segments: string[]
  }

  emoji_sentiment?: {
    score: number
    emojis: string[]
    assignment_reason: string
  }

  hashtag_sentiment?: {
    score: number
    hashtags: string[]
  }

  sarcasm_detected: boolean
  sarcasm_reasoning?: string

  threat_level: number
  threat_reasoning: string
}

export interface ComparativeAnalysis {
  has_comparison: boolean
  comparison_type: 'Direct Contrast' | 'Implicit' | 'Neutral Coexistence' | 'None'
  entities_compared: string[]
  relationship: string
  context_segments: string[]
}

export interface Post {
  id: string
  platform: string
  post_text: string
  author_username: string
  posted_at: string

  // NEW: Multi-entity sentiment
  entity_sentiments?: Record<string, EntitySentiment>
  comparative_analysis?: ComparativeAnalysis

  // LEGACY: Overall sentiment (calculated from entities)
  sentiment_score: number
  sentiment_label: string

  // Engagement
  likes: number
  comments: number
  shares: number
  views: number

  // Other fields...
}
```

### Step 2: Update PostCard Component

**File:** `/frontend/src/components/PostCard.vue`

**ADD AFTER EXISTING CONTENT (before closing </template>):**
```vue
<!-- Multi-Entity Sentiment Analysis Section -->
<div v-if="post.entity_sentiments && Object.keys(post.entity_sentiments).length > 0"
     class="entity-sentiments mt-4 border-t pt-4">
  <h4 class="text-sm font-semibold text-gray-700 mb-2">Entity Sentiment Analysis:</h4>

  <div class="entity-badges flex flex-wrap gap-2">
    <div
      v-for="(sentiment, entity) in post.entity_sentiments"
      :key="entity"
      :class="[
        'entity-badge px-3 py-1.5 rounded-lg border-2 flex items-center space-x-2',
        getSentimentClass(sentiment.label)
      ]"
    >
      <span class="entity-name font-bold">{{ entity }}</span>
      <span class="sentiment-score text-sm font-mono">
        {{ sentiment.score > 0 ? '+' : '' }}{{ sentiment.score.toFixed(2) }}
      </span>
      <span class="sentiment-label text-xs uppercase">{{ sentiment.label }}</span>
      <span class="confidence text-xs opacity-75">
        ({{ (sentiment.confidence * 100).toFixed(0) }}%)
      </span>

      <!-- Sarcasm indicator -->
      <span v-if="sentiment.sarcasm_detected" class="sarcasm-badge ml-1" title="Sarcasm detected">
        🙄
      </span>

      <!-- Threat indicator -->
      <span v-if="sentiment.threat_level > 0.3"
            :class="['threat-badge ml-1', getThreatClass(sentiment.threat_level)]"
            :title="sentiment.threat_reasoning">
        ⚠️
      </span>
    </div>
  </div>

  <!-- Comparative analysis indicator -->
  <div v-if="post.comparative_analysis?.has_comparison"
       class="comparison-badge mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-sm">
    <div class="flex items-center space-x-2">
      <svg class="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
      <span class="text-blue-800 font-medium">
        {{ post.comparative_analysis.comparison_type }}:
      </span>
      <span class="text-blue-700">
        {{ post.comparative_analysis.relationship }}
      </span>
    </div>
  </div>
</div>
```

**ADD TO SCRIPT SETUP:**
```vue
<script setup>
// ... existing imports ...

const getSentimentClass = (label) => {
  const classes = {
    'Positive': 'bg-green-50 border-green-300 text-green-800',
    'Negative': 'bg-red-50 border-red-300 text-red-800',
    'Neutral': 'bg-gray-50 border-gray-300 text-gray-700'
  }
  return classes[label] || classes['Neutral']
}

const getThreatClass = (level) => {
  if (level >= 0.7) return 'text-red-600'
  if (level >= 0.5) return 'text-orange-600'
  return 'text-yellow-600'
}
</script>
```

---

## 🚀 Testing

### Manual Test Cases

**Test 1: Single Entity Positive**
```
Post: "DMK's healthcare policy is excellent! 👍 #SupportDMK"
Expected:
- entity_sentiments.DMK.label = "Positive"
- entity_sentiments.DMK.score ≈ 0.7-0.8
- comparative_analysis.has_comparison = false
```

**Test 2: Comparative (DMK vs BJP)**
```
Post: "DMK's healthcare is excellent 👍 but BJP's approach has failed 👎"
Expected:
- entity_sentiments.DMK.label = "Positive" (score ≈ 0.75)
- entity_sentiments.BJP.label = "Negative" (score ≈ -0.65)
- comparative_analysis.has_comparison = true
- comparative_analysis.comparison_type = "Direct Contrast"
```

**Test 3: Emoji Applies to All**
```
Post: "#DMK #BJP are both doing great work! 🎉"
Expected:
- entity_sentiments.DMK.emoji_sentiment.emojis includes "🎉"
- entity_sentiments.BJP.emoji_sentiment.emojis includes "🎉"
- Both positive sentiment
```

**Test 4: Sarcasm Detection**
```
Post: "Great job BJP! /s"
Expected:
- entity_sentiments.BJP.label = "Negative"
- entity_sentiments.BJP.sarcasm_detected = true
- entity_sentiments.BJP.score < 0
```

**Test 5: Pronoun Resolution**
```
Post: "BJP policies failed. Their approach is completely wrong."
Expected:
- entity_sentiments.BJP mentioned
- "Their approach" attributed to BJP
- Negative sentiment
```

---

## 📝 QUICK START CHECKLIST

1. **✅ Schema Updated** - `posts_table.py` has new fields
2. **✅ LLM Prompt Created** - Multi-entity analysis implemented
3. **⏳ Update Pipeline** - Modify `pipeline_orchestrator.py` to call `analyze_post_multi_entity()`
4. **⏳ Create API Endpoints** - Add `entity_analytics.py` router
5. **⏳ Run Migration** - Execute migration script to convert old data
6. **⏳ Update Frontend** - Add TypeScript types and update components
7. **⏳ Test** - Verify with sample posts from each test case

---

## 🎯 Next Action

**IMMEDIATE:** Update `pipeline_orchestrator.py` line ~160-180 to use multi-entity analysis.

**COMMAND:**
```bash
# Find the exact location
cd /Users/Samrt\ radar\ Final\ /backend
grep -n "process_post" app/services/pipeline_orchestrator.py
```

Then apply the changes outlined in "Step 1: Update PipelineOrchestrator" above.

---

## 📞 Support

For questions or issues:
1. Check this document first
2. Review test cases for expected behavior
3. Check logs for LLM response errors
4. Verify cluster configuration (DMK/ADMK/BJP/TVK)

**Key Files:**
- Schema: `/backend/app/models/posts_table.py:90-120`
- LLM: `/backend/app/services/llm_processing_service.py:533-888`
- Pipeline: `/backend/app/services/pipeline_orchestrator.py` (to be updated)
- Frontend: `/frontend/src/components/PostCard.vue` (to be updated)
