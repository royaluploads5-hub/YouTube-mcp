# YouTube Remote MCP for Claude

This is a small single-user remote MCP server that exposes:
- youtube_auth_url
- youtube_auth_status
- upload_video

It uses the official YouTube Data API and OAuth.

## Important
Do not commit Google Client Secret or OAuth tokens to GitHub.

## Deploy
Deploy this repository as a Python web service on Render (or another public HTTPS host).

Set environment variables:
GOOGLE_CLIENT_ID = your Google OAuth Web client ID
GOOGLE_CLIENT_SECRET = your Google OAuth Web client secret
GOOGLE_REDIRECT_URI = https://YOUR-RENDER-DOMAIN/oauth2callback

After the Render URL is known, add exactly that callback URL to the Google OAuth client's
Authorized redirect URIs.

## Claude
Use the public MCP endpoint:
https://YOUR-RENDER-DOMAIN/mcp

Add it in Claude:
Customize -> Connectors -> Add -> Add custom connector.

## First authorization
After the connector is connected, call youtube_auth_url and open the returned Google URL.
Approve YouTube access. Then call youtube_auth_status.

## Upload
The upload tool accepts a public HTTPS video URL. It defaults to private uploads.
