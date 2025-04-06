/*
  # Create user preferences table with role management

  1. New Types
    - `user_role` enum type for role selection (customer/runner)

  2. New Tables
    - `user_preferences`
      - `user_id` (uuid, primary key, references auth.users)
      - `active_role` (user_role, default: customer)
      - `previous_role` (user_role, nullable)
      - `updated_at` (timestamptz)

  3. Security
    - Enable RLS on user_preferences table
    - Add policy for users to manage their own preferences
*/

-- Create role type enum
CREATE TYPE user_role AS ENUM ('customer', 'runner');

-- Create user preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id),
  active_role user_role DEFAULT 'customer',
  previous_role user_role,
  updated_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Policies for user preferences
CREATE POLICY "Users can manage their own preferences"
  ON user_preferences
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);