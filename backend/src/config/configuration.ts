import { registerAs } from '@nestjs/config';

function requireEnv(name: string): string {
  const value = process.env[name];
  if (value === undefined) {
    throw new Error(`Missing environment variable: ${name}`);
  }
  return value;
}

export const appConfig = registerAs('app', () => ({
  nodeEnv: requireEnv('NODE_ENV'),
  port: Number(requireEnv('PORT')),
}));

export const databaseConfig = registerAs('database', () => ({
  url: requireEnv('DATABASE_URL'),
}));

export const jwtConfig = registerAs('jwt', () => ({
  secret: requireEnv('JWT_SECRET'),
  expiresIn: requireEnv('JWT_EXPIRES_IN'),
}));

export const elasticsearchConfig = registerAs('elasticsearch', () => ({
  url: requireEnv('ELASTICSEARCH_URL'),
  user: requireEnv('ELASTICSEARCH_USER'),
  // Empty in development until #17 enables Elasticsearch security
  password: process.env.ELASTICSEARCH_PASSWORD || undefined,
}));
