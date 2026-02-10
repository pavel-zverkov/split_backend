-- Enable PostGIS extension for geospatial data
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enable UUID generation (useful for tokens, invite codes)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable case-insensitive text (useful for usernames, emails)
CREATE EXTENSION IF NOT EXISTS citext;

-- Enable trigram for fuzzy text search (useful for user search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
