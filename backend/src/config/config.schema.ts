import * as Joi from 'joi';

export const configSchema = Joi.object({
  NODE_ENV: Joi.string()
    .valid('development', 'production', 'test')
    .default('development'),
  PORT: Joi.number().port().min(1024).max(49151).default(3001),
  DATABASE_URL: Joi.string()
    .uri({ scheme: ['postgres', 'postgresql'] })
    .required(),
  POSTGRES_USER: Joi.string().required(),
  POSTGRES_PASSWORD: Joi.string().required(),
  POSTGRES_DB: Joi.string().required(),

  // openssl rand -hex 32 → 64 chars.
  JWT_SECRET: Joi.string().min(64).required(),
  JWT_EXPIRES_IN: Joi.string()
    .pattern(/^\d+[smhd]$/)
    .required(),

  ELASTICSEARCH_URL: Joi.string()
    .uri({ scheme: ['http', 'https'] })
    .required(),

  ELASTICSEARCH_USER: Joi.string().required(),
  ELASTICSEARCH_PASSWORD: Joi.when('NODE_ENV', {
    is: 'production',
    then: Joi.string().min(32).required(),
    otherwise: Joi.string().allow('').optional(),
  }),

  VIRUSTOTAL_API_KEY: Joi.string().allow('').optional(),
});
