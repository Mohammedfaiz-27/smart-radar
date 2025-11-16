# LLM Processing Flow & Performance

## Current Processing Architecture

### 1. Batch Configuration
```python
# PipelineOrchestrator (process_pending_raw_data)
batch_size = 20  # Process 20 entries at once

# LLMProcessingService  
self.batch_size = 50  # Internal batch size (not used in sequential flow)
```

### 2. Processing Flow (SEQUENTIAL - SLOW)

```
raw_data entries (791 pending)
       ↓
Pipeline fetches 100 entries
       ↓
Split into batches of 20
       ↓
FOR EACH entry in batch (SEQUENTIAL):
  ├── Extract post from raw_json
  ├── Call Gemini API (BLOCKING, ~1-3 seconds per call)
  ├── Parse JSON response
  └── Create PostCreate object
       ↓
Bulk save batch to posts_table (20 posts)
       ↓
Mark raw_data as processed
       ↓
Sleep 0.5s between batches
```

## Performance Bottleneck

**Issue**: Each post is processed ONE AT A TIME (sequential)
- Line 396-402 in pipeline_orchestrator.py uses a `for` loop
- Each LLM call takes 1-3 seconds
- Batch of 20 = 20-60 seconds per batch
- 791 pending / 20 = ~40 batches
- **Total time: 13-40 minutes for all pending entries**

## Current Speed
- **Per post**: 1-3 seconds (Gemini API call)
- **Per batch** (20 posts): 20-60 seconds (sequential)
- **Overall**: ~100 posts in 5-15 minutes

## Solution: Parallelize LLM Calls

Change from:
```python
# SLOW - Sequential
for entry in batch:
    post = await self.llm_service.process_raw_data(entry)
```

To:
```python
# FAST - Parallel
tasks = [self.llm_service.process_raw_data(entry) for entry in batch]
posts = await asyncio.gather(*tasks, return_exceptions=True)
```

**Expected improvement**: 
- 20 posts in ~3-5 seconds (all parallel)
- **10-20x faster** overall processing
