# Disputes

A dispute, also called a chargeback, is opened when a customer asks their bank to reverse a payment.

## Dispute lifecycle

A dispute has the status open, under_review, won or lost. When a dispute is opened, the disputed amount is held from your next settlement until the dispute is resolved.

## Responding to a dispute

You must respond to a dispute within 7 days of the dispute.created event. Submit evidence such as an invoice, a delivery confirmation and customer communication through the /disputes/{dispute_id}/evidence endpoint. A dispute with no response after 7 days is automatically marked as lost.

## Dispute fees

A lost dispute incurs a dispute fee of 500 rupees. No fee is charged when a dispute is won.
