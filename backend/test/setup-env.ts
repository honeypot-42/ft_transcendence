import { randomBytes } from 'node:crypto';

/*
 * Test-only environment so AppModule passes the config validation in CI,
 * where there is no .env. Secrets are generated on every run: nothing real
 * is committed and real values from the shell are never used by the tests.
 */
const dbPassword = randomBytes(16).toString('hex');

process.env.NODE_ENV = 'test';
process.env.PORT = '3001';
process.env.POSTGRES_USER = 'sentinel_test';
process.env.POSTGRES_PASSWORD = dbPassword;
process.env.POSTGRES_DB = 'sentinel_test';
process.env.DATABASE_URL = `postgresql://sentinel_test:${dbPassword}@localhost:5432/sentinel_test`;
process.env.JWT_SECRET = randomBytes(32).toString('hex');
process.env.JWT_EXPIRES_IN = '15m';
process.env.ELASTICSEARCH_URL = 'http://localhost:9200';
process.env.ELASTICSEARCH_USER = 'sentinel_test';
process.env.ELASTICSEARCH_PASSWORD = '';
process.env.VIRUSTOTAL_API_KEY = '';
