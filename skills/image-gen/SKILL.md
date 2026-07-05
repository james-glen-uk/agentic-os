# Image Generation

Generate an image from a text prompt via the configured media provider.

**Code-backed skill.** Calls `POST /api/media/image` with a prompt and an
optional style preset (photo / illustration / 3d / pixel). The result is
saved to the Artifact Library as an image artifact and previewed inline.

## Configuration (data/settings.json)

```json
{
  "media": { "image_provider": "gemini" },
  "api_keys": { "gemini": "..." }
}
```

If no provider is configured, the endpoint returns a clear setup message
rather than failing — configure a provider and key in Settings to enable it.

Primary: gemini
