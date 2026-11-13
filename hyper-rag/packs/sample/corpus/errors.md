# Errors and rate limits

Lumen Pay uses standard HTTP status codes and returns an error object with a code and a description.

## Error codes

The error code bad_request means a required field is missing or malformed and is returned with HTTP status 400. The error code authentication_failed means the API key is wrong and is returned with HTTP status 401. The error code gateway_error means the bank did not respond and is returned with HTTP status 502.

## Rate limits

The API allows 100 requests per second per account in live mode and 25 requests per second in test mode. A request over the limit receives HTTP status 429 with a Retry-After header that states how many seconds to wait.

## Retrying safely

Retry requests that fail with status 429 or 502 using exponential backoff. Always send the same Idempotency-Key when retrying a POST request so the operation is not performed twice.
