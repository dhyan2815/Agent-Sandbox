# Refunds

Refunds return money from a captured payment to the customer's original payment method.

## Creating a refund

Create a refund by sending a POST request to /payments/{payment_id}/refunds. Omit the amount field to refund the full payment, or pass an amount to issue a partial refund. A payment can receive several partial refunds as long as their total does not exceed the captured amount.

## Refund timelines

A normal refund reaches the customer within 5 to 7 business days. An instant refund reaches the customer within 30 minutes and costs an additional fee of 1 percent of the refunded amount.

## Refund window

A refund can be created up to 180 days after the payment was captured. After 180 days the refund request is rejected with the error code refund_window_expired.

## Refund statuses

A refund has the status pending, processed or failed. A failed refund is retried automatically once after 24 hours.
