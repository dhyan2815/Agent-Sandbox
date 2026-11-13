# Payments

A payment represents one attempt by a customer to pay an order.

## Creating a payment

Create a payment by sending a POST request to /payments with an amount, a currency and an order_id. The amount is always expressed in the smallest currency unit, so 500 rupees is sent as 50000 paise. The minimum payment amount is 100 paise.

## Payment statuses

A payment moves through the statuses created, authorized, captured and failed. An authorized payment has been approved by the bank but the money has not yet been taken from the customer.

## Capturing a payment

An authorized payment must be captured within 5 days. A payment that is not captured within 5 days is automatically voided and the hold on the customer's funds is released. Set the capture_mode field to automatic to capture every payment as soon as it is authorized.

## Idempotency

Send an Idempotency-Key header with every POST request. Lumen Pay stores idempotency keys for 24 hours and returns the original response when the same key is sent again.
