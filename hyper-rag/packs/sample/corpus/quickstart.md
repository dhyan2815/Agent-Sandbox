# Lumen Pay quickstart

Lumen Pay is a fictional payments API used as sample data for Hyper-RAG.

## API keys

Every request is authenticated with an API key pair: a key ID and a key secret. Generate the key pair from the Lumen Pay dashboard under Settings, then API Keys. The key secret is shown only once at creation time, so store it in a secrets manager.

Requests use HTTP Basic authentication with the key ID as the username and the key secret as the password.

## Test mode and live mode

Each account has two modes. Test mode keys start with the prefix lk_test_ and never move real money. Live mode keys start with the prefix lk_live_ and are available only after account verification is complete.

## Base URL

All API endpoints are served from https://api.lumenpay.example/v2. The API accepts JSON request bodies and returns JSON responses.

## SDKs

Official SDKs are available for Python, Node.js and Java. The Python SDK is installed with pip install lumenpay.
