# Postiz Integration Guide

## Overview

KaiTian integrates with Postiz to provide social media publishing capabilities. Postiz is a unified social media scheduling and publishing platform that supports 32+ social networks.

## What is Postiz?

Postiz allows you to manage and publish content to multiple social media platforms through a single API:
- **Reddit** - Text and link posts to subreddits
- **Twitter/X** - Tweets, threads, and replies
- **LinkedIn** - Professional posts and articles
- **Facebook, Instagram, TikTok** - And 28+ other platforms

## Setup

### 1. Get Postiz API Key

1. Sign up at [Postiz](https://postiz.com) or use a self-hosted instance
2. Go to Settings → API Keys
3. Create a new API key
4. Add to your `.env` file:
   ```env
   POSTIZ_API_KEY=your_api_key_here
   ```

### 2. Create Postiz Integrations (Connected Accounts)

Before publishing, you need to connect your social media accounts in Postiz:

1. In Postiz UI, go to "Channels" or "Integrations"
2. Connect your Reddit account
3. Connect your Twitter/X account
4. Note the integration IDs (you'll need these for API calls)

### 3. Add Integration IDs to KaiTian

Update your `.env` file with the integration IDs from Postiz:

```env
POSTIZ_REDDIT_INTEGRATION_ID=your_reddit_integration_id
POSTIZ_TWITTER_INTEGRATION_ID=your_twitter_integration_id
```

## KaiTian API Endpoints

### Post to Reddit

**Endpoint:** `POST /api/v1/post/reddit`

**Request Parameters:**
```json
{
  "post_id": "string (KaiTian post ID)",
  "reply_text": "string (content to post)",
  "reddit_integration_id": "string (optional - uses env var if not provided)"
}
```

**Response:**
```json
{
  "success": true,
  "post_id": "uuid",
  "platform": "reddit",
  "published": true,
  "published_id": "postiz_post_id",
  "postiz_post_id": "postiz_post_id",
  "published_at": "2024-12-14T10:00:00.000Z"
}
```

**How it works:**
1. Takes a KaiTian post ID from the database
2. Calls Postiz API to publish the reply text
3. Updates the post status to "published"
4. Returns the Postiz post ID for tracking

### Post to Twitter/X

**Endpoint:** `POST /api/v1/post/twitter`

**Request Parameters:**
```json
{
  "post_id": "string (KaiTian post ID)",
  "reply_text": "string (tweet content)",
  "twitter_integration_id": "string (optional - uses env var if not provided)"
}
```

**Response:**
```json
{
  "success": true,
  "post_id": "uuid",
  "platform": "twitter",
  "published": true,
  "published_id": "postiz_post_id",
  "postiz_post_id": "postiz_post_id",
  "published_at": "2024-12-14T10:00:00.000Z"
}
```

**How it works:**
1. Takes a KaiTian post ID from the database
2. Calls Postiz API to publish the tweet
3. Updates the post status to "published"
4. Returns the Postiz post ID for tracking

## n8n Workflow Integration

### Example: Reddit Publishing Workflow

```
[Start] → [Get Posts] → [AI Analysis] → [Human Review] → [Publish to Reddit] → [End]
```

**Step 1: Get Posts from KaiTian**
```
HTTP Request Node
Method: GET
URL: http://localhost:8000/api/v1/posts?status=reply_generated
```

**Step 2: Publish to Reddit** 
```
HTTP Request Node
Method: POST
URL: http://localhost:8000/api/v1/post/reddit
Body:
{
  "post_id": "{{ $json.posts[0].id }}",
  "reply_text": "{{ $json.posts[0].generated_reply }}"
}
```

**Step 3: Handle Response**
- If `success` is `true`: Post was published successfully
- If `success` is `false`: Check `error` field for details

### Example: Twitter Publishing Workflow

```
[Start] → [Get Posts] → [AI Analysis] → [Human Review] → [Publish to Twitter] → [End]
```

**Step: Publish to Twitter**
```
HTTP Request Node
Method: POST
URL: http://localhost:8000/api/v1/post/twitter
Body:
{
  "post_id": "{{ $json.posts[0].id }}",
  "reply_text": "{{ $json.posts[0].generated_reply }}"
}
```

## Architecture

### Postiz Client (`app/integrations/postiz_client.py`)

The Postiz client handles:
- API authentication with your Postiz API key
- Building correct request payloads for each platform
- Error handling and logging
- Async HTTP requests to Postiz API

**Key Methods:**
- `post_to_reddit()` - Publish text or link posts to Reddit
- `post_to_twitter()` - Publish tweets (with thread support)
- `get_integrations()` - List available connected accounts

### Publishing Flow

```
n8n sends HTTP request
    ↓
KaiTian API endpoint receives request
    ↓
Fetch post from database
    ↓
Validate Postiz integration ID
    ↓
Call Postiz API with publication payload
    ↓
Update KaiTian post status to "published"
    ↓
Return success response with Postiz post ID
```

### Post Status Tracking

Posts flow through statuses:
- `pending` - Initial state
- `fetched` - Successfully fetched from social media
- `analyzed` - AI analysis completed
- `relevant` - Marked as relevant to respond to
- `reply_generated` - Reply text generated
- `reply_approved` - Human approved the reply
- `published` - Successfully published to social media
- `failed` - Publishing failed

## Error Handling

### Common Errors

**"Postiz API key not configured"**
- Ensure `POSTIZ_API_KEY` is set in `.env`

**"Reddit integration ID not configured"**
- Ensure `POSTIZ_REDDIT_INTEGRATION_ID` is set in `.env`
- Make sure you've connected your Reddit account in Postiz

**"Post not found"**
- Ensure the `post_id` exists in KaiTian database
- The post must have been fetched and stored first

**"Postiz API error: 401"**
- Your API key is invalid or expired
- Check your Postiz dashboard for active API keys

**"Postiz API error: 429"**
- Rate limit exceeded (30 requests per hour)
- Wait before making more API calls

### Debugging

Enable debug logging to see full Postiz API requests/responses:
```env
LOG_LEVEL=DEBUG
```

Check logs for:
- API request payloads sent to Postiz
- Full error messages from Postiz
- Published post IDs returned

## Supported Post Types

### Reddit

- **Self posts** (text) - Default type
- **Link posts** - Specify URL
- **Image posts** - Upload images to Postiz first
- **Video posts** - Upload videos to Postiz first
- **Cross-posts** - Post to multiple subreddits

### Twitter

- **Simple tweets** - Single message
- **Threads** - Multiple connected tweets
- **Reply settings** - Control who can reply (everyone, following, verified, etc.)

## Rate Limits

Postiz enforces **30 requests per hour** API rate limit.

Each API call counts as one request, regardless of:
- Number of posts published
- Number of platforms targeted
- Scheduling vs immediate publishing

**Optimization tip:** Schedule multiple posts in bulk to maximize throughput.

## Examples

### Complete n8n Workflow JSON

Save this as a workflow in n8n:

```json
{
  "nodes": [
    {
      "parameters": {
        "resource": "httpRequest",
        "url": "http://localhost:8000/api/v1/posts?status=reply_approved",
        "method": "GET"
      },
      "name": "Get Posts to Publish",
      "type": "n8n-nodes-base.httpRequest",
      "position": [250, 300]
    },
    {
      "parameters": {
        "resource": "httpRequest",
        "url": "http://localhost:8000/api/v1/post/reddit",
        "method": "POST",
        "jsonParameters": true,
        "requestBody": "{\"post_id\": \"{{ $json.posts[0].id }}\", \"reply_text\": \"{{ $json.posts[0].generated_reply }}\"}"
      },
      "name": "Publish to Reddit",
      "type": "n8n-nodes-base.httpRequest",
      "position": [450, 300]
    },
    {
      "parameters": {
        "resource": "httpRequest",
        "url": "http://localhost:8000/api/v1/post/twitter",
        "method": "POST",
        "jsonParameters": true,
        "requestBody": "{\"post_id\": \"{{ $json.posts[0].id }}\", \"reply_text\": \"{{ $json.posts[0].generated_reply }}\"}"
      },
      "name": "Publish to Twitter",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300]
    }
  ],
  "connections": {
    "Get Posts to Publish": {
      "main": [
        [
          {
            "node": "Publish to Reddit",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

## Troubleshooting

### Posts not being published

1. Check that Postiz API key is valid
2. Verify integration IDs match your Postiz account
3. Ensure accounts are connected in Postiz UI
4. Check n8n logs for HTTP errors
5. Verify post status is "reply_approved" or similar

### Wrong content being published

1. Check the `reply_text` parameter in your n8n request
2. Verify the generated_reply field in database
3. Test with a simple hardcoded message first

### Rate limit issues

1. Space out API calls over time
2. Batch multiple posts in a single request if possible
3. Monitor your Postiz usage dashboard
4. Wait at least 2 hours before sending 30+ requests again

## Next Steps

1. [Set up n8n workflow](./N8N_INTEGRATION.md)
2. [Configure Reddit API credentials](./DATABASE_CRAWLER_INTEGRATION.md#reddit-setup)
3. [Start the KaiTian server](../IMPLEMENTATION_GUIDE.md#starting-the-server)
4. [Test the endpoints](./DATABASE_CRAWLER_INTEGRATION.md#testing)

## More Information

- [Postiz Official Docs](https://docs.postiz.com)
- [Postiz Public API](https://docs.postiz.com/public-api/introduction)
- [n8n Integration Guide](./N8N_INTEGRATION.md)
- [KaiTian Database Guide](./DATABASE_CRAWLER_INTEGRATION.md)
