# Google Custom Search API Setup Guide

This guide explains how to set up and use Google Custom Search API for image search in OmniPush.

## Overview

OmniPush now supports two image search providers:
- **Google Custom Search API** (recommended, default)
- **SerpAPI** (legacy, optional)

## Why Google Custom Search API?

- Official Google API with stable, documented interface
- More cost-effective for moderate usage (100 free queries/day)
- No third-party dependencies (unlike SerpAPI)
- Better control over search parameters and filters

## Setup Instructions

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable billing for the project (required for API access)

### Step 2: Enable Custom Search API

1. Go to [APIs & Services > Library](https://console.cloud.google.com/apis/library)
2. Search for "Custom Search API"
3. Click on "Custom Search API" and click "Enable"

### Step 3: Create API Credentials

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" > "API Key"
3. Copy the generated API key
4. (Recommended) Click "Restrict Key" to add restrictions:
   - Under "API restrictions", select "Restrict key"
   - Select "Custom Search API" from the dropdown
   - Click "Save"

### Step 4: Create a Programmable Search Engine

1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click "Add" or "Create a new search engine"
3. Configure your search engine:
   - **Sites to search**: Enter `*` to search the entire web
   - **Name**: Give it a meaningful name (e.g., "OmniPush Image Search")
   - **Search engine keywords**: Optional, can leave blank
4. Click "Create"
5. On the next page, find your **Search engine ID** (also called CX)
6. Copy the Search engine ID

### Step 5: Enable Image Search

1. In the Programmable Search Engine control panel
2. Click on your search engine
3. Click "Setup" > "Basic"
4. Under "Search features", enable:
   - ✅ **Image search**: ON
   - ✅ **Safe search**: ON (recommended)
5. Click "Update"

### Step 6: Configure OmniPush Backend

1. Open your `.env` file in the `omnipush-backend` directory
2. Add or update the following configuration:

```bash
# Image Search Configuration
IMAGE_SEARCH_PROVIDER=google_custom_search

# Google Custom Search Configuration
GOOGLE_CUSTOM_SEARCH_API_KEY=your_actual_api_key_here
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_search_engine_id_here
```

3. Replace the placeholder values:
   - `GOOGLE_CUSTOM_SEARCH_API_KEY`: Paste your API key from Step 3
   - `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`: Paste your Search Engine ID from Step 4

### Step 7: Restart the Backend

```bash
# Stop the current backend process (Ctrl+C)

# Restart using one of these methods:
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

# OR using the start script
./start-omnipush.sh restart
```

## Verification

To verify the setup is working:

1. Check the backend logs on startup. You should see:
   ```
   INFO: Image search service initialized with provider: google_custom_search
   ```

2. Test auto-image search:
   - Create a post with auto-image search enabled on a social account
   - Add an `image_search_caption` to the post
   - Publish the post
   - Check logs for successful image search and download

## Usage Limits and Pricing

### Free Tier
- **100 queries per day** for free
- Suitable for development and small-scale usage

### Paid Tier
- $5 per 1,000 queries (after free tier)
- Up to 10,000 queries per day

### Monitoring Usage
1. Go to [Google Cloud Console > APIs & Services > Dashboard](https://console.cloud.google.com/apis/dashboard)
2. Click on "Custom Search API"
3. View your usage metrics and quotas

## Switching Between Providers

You can switch between providers at any time by changing the `IMAGE_SEARCH_PROVIDER` setting:

### Use Google Custom Search (Recommended)
```bash
IMAGE_SEARCH_PROVIDER=google_custom_search
GOOGLE_CUSTOM_SEARCH_API_KEY=your_api_key
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_cx_id
```

### Use SerpAPI (Legacy)
```bash
IMAGE_SEARCH_PROVIDER=serpapi
SERPAPI_KEY=your_serpapi_key
```

After changing the provider, restart the backend service.

## Troubleshooting

### Error: "Google Custom Search API key or Search Engine ID not configured"

**Solution**: Make sure both `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` are set in your `.env` file.

### Error: "API key not valid"

**Solutions**:
1. Verify the API key is correct (no extra spaces or characters)
2. Check that Custom Search API is enabled for your project
3. Ensure API key restrictions allow Custom Search API

### Error: "Quota exceeded"

**Solutions**:
1. Check your daily quota in Google Cloud Console
2. Wait until the next day for the quota to reset
3. Upgrade to paid tier for higher limits

### Error: "No images found"

**Possible causes**:
1. Search term is too specific or unusual
2. Safe search filtering is blocking results
3. Search engine is not configured for entire web (should use `*`)

**Solutions**:
1. Try broader search terms
2. Adjust safe search settings in Programmable Search Engine
3. Verify search engine configuration includes `*` for sites to search

### Images fail to download

**Solutions**:
1. Check network connectivity
2. Verify S3 storage is properly configured
3. Check image URL accessibility and CORS settings
4. Review backend logs for specific error messages

## API Reference

### Google Custom Search API v1

**Endpoint**: `https://www.googleapis.com/customsearch/v1`

**Parameters**:
- `key`: Your API key
- `cx`: Your Search Engine ID
- `q`: Search query
- `searchType`: `image` for image search
- `num`: Number of results (1-10)
- `safe`: Safe search level (`active`, `off`)

**Response Structure**:
```json
{
  "items": [
    {
      "title": "Image title",
      "link": "https://example.com/image.jpg",
      "displayLink": "example.com",
      "image": {
        "contextLink": "https://example.com/page",
        "height": 1080,
        "width": 1920
      }
    }
  ]
}
```

## Best Practices

1. **API Key Security**: Never commit API keys to version control. Use `.env` file and add it to `.gitignore`.

2. **Error Handling**: The service automatically retries with the next image result if one fails to download.

3. **Attribution**: Image metadata includes source information for proper attribution.

4. **Rate Limiting**: Monitor your API usage to stay within quotas.

5. **Search Quality**: Use descriptive search terms for better image results.

## Support

For issues or questions:
- Check the [Google Custom Search API documentation](https://developers.google.com/custom-search/v1/introduction)
- Review backend logs for detailed error messages
- Contact the development team with specific error details

## Migration from SerpAPI

If you're migrating from SerpAPI:

1. Set up Google Custom Search as described above
2. Update `.env` with Google Custom Search credentials
3. Change `IMAGE_SEARCH_PROVIDER=google_custom_search`
4. Restart the backend
5. Test the image search functionality
6. (Optional) Remove SerpAPI configuration if no longer needed

The service interface remains the same, so no code changes are required.
