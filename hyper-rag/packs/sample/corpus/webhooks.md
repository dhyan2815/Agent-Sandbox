# Webhooks

Webhooks notify your server when an event happens in your Lumen Pay account.

## Events

Subscribe to events such as payment.captured, payment.failed, refund.processed and dispute.created from the dashboard. Each webhook request is a POST with a JSON body that contains the event name and the affected object.

## Verifying signatures

Every webhook request carries an X-Lumen-Signature header. The signature is an HMAC-SHA256 digest of the raw request body, computed with your webhook secret. Compare the digest using a constant-time comparison and reject the request if it does not match.

## Responding and retries

Your endpoint must respond with a 2xx status code within 5 seconds. If it does not, Lumen Pay retries the delivery with exponential backoff for up to 24 hours. After 24 hours of failed deliveries the webhook is marked as disabled.

## Duplicate events

The same event can be delivered more than once. Use the event_id field to ignore events your server has already processed.
