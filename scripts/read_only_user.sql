-- 1. Create the user with a secure password
CREATE USER polaris_reader WITH PASSWORD 'polaris_reader';

-- 2. Grant connection rights to the polaris database
GRANT CONNECT ON DATABASE polaris TO polaris_reader;

-- 3. Grant usage rights to the public schema (where tables live)
GRANT USAGE ON SCHEMA public TO polaris_reader;

-- 4. Grant read-only select permissions on all EXISTING tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO polaris_reader;

-- 5. Automatically grant read-only permissions on all FUTURE tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO polaris_reader;
