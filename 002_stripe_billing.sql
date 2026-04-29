-- BugOracle: Stripe billing migration
-- Run once via the /run-migration pattern or Render Shell
-- File: migrations/002_stripe_billing.sql

-- Add Stripe customer and subscription tracking to users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS stripe_customer_id      VARCHAR(255),
    ADD COLUMN IF NOT EXISTS stripe_subscription_id  VARCHAR(255);

-- Index for fast webhook lookups by subscription ID
CREATE INDEX IF NOT EXISTS idx_users_stripe_subscription
    ON users (stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;

-- Index for customer lookups
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer
    ON users (stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;