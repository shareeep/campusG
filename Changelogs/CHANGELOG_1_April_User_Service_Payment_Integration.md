# Changelog - April 1, 2025 - User Service Payment Integration

This update integrates the User Service more deeply into the payment processing flow, particularly for the Create Order Saga.

## Key Changes:

1.  **Automatic Stripe Customer Creation:**
    *   Modified the Clerk webhook handler (`handle_user_created` in `app/api/user_routes.py`) to automatically create a Stripe Customer via the Stripe API when a new user is registered through Clerk.
    *   The resulting `stripeCustomerId` is now saved to the `User` model in the User Service database.

2.  **Kafka Integration for Payment Data Retrieval:**
    *   Standardized the Kafka client library for User Service to `kafka-python` (version 2.0.2), replacing `confluent-kafka` in `requirements.txt` for consistency with the Create Order Saga.
    *   Implemented `app/services/kafka_service.py` using `kafka-python`.
    *   Added a Kafka consumer that listens on the `user_commands` topic (configurable via `KAFKA_USER_COMMANDS_TOPIC`).
    *   The consumer processes `get_user_payment_info` requests, retrieving the user's `stripeCustomerId` and default `payment_method_id` from the database.
    *   Added a Kafka producer that publishes `user.payment_info_retrieved` events to the `user_events` topic (configurable via `KAFKA_USER_EVENTS_TOPIC`) upon successful data retrieval, including the necessary `correlation_id`.
    *   Publishes `user.payment_info_failed` events if the required user data (Stripe ID, payment method) is missing or an error occurs.
    *   Integrated the Kafka service initialization (`init_kafka`) into the Flask application factory (`app/__init__.py`) to start the consumer when the service runs.

## Impact:

*   New users registered via Clerk will now automatically have a corresponding Stripe Customer record created.
*   The User Service can now respond to requests from the Create Order Saga (and potentially other sagas) by providing necessary payment details (`stripeCustomerId`, `payment_method_id`) via Kafka events, enabling the saga to proceed with payment authorization through the Payment Service.
*   This aligns the User Service with the documented payment flow: User Service → Kafka (user\_events) → Create Order Saga → Kafka (payment\_commands) → Payment Service → Stripe.
