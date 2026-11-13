# UPI payments

Lumen Pay supports UPI through two flows: collect and intent.

## Collect flow

In the collect flow the customer enters a UPI ID and approves a payment request inside their UPI app. A collect request expires after 5 minutes if the customer does not approve it.

## Intent flow

In the intent flow your mobile app opens the customer's UPI app directly with the payment details filled in. The intent flow has a higher success rate than the collect flow because the customer does not type a UPI ID.

## Limits

A single UPI payment cannot exceed 100000 rupees. Payments above this limit fail with the error code upi_limit_exceeded.

## UPI refunds

UPI payments are refunded to the same UPI ID that made the payment. Instant refunds are supported for UPI payments.
