import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module.js';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);

  // Global validation pipe — enforces DTOs with class-validator
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,       // Strip unknown properties
      forbidNonWhitelisted: true, // Throw on unknown properties
      transform: true,       // Auto-transform payloads to DTO instances
    }),
  );

  // Global API prefix
  app.setGlobalPrefix('api/v1');

  const port = process.env['PORT'] ?? 3001;
  await app.listen(port);
  console.log(`🚀 SENTINEL backend running on: http://localhost:${port}`);
}

void bootstrap();
