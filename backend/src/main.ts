import { NestFactory } from '@nestjs/core';
import { Logger, ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);

  // Global validation pipe — enforces DTOs with class-validator
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true, // Strip unknown properties
      forbidNonWhitelisted: true, // Throw on unknown properties
      transform: true, // Auto-transform payloads to DTO instances
    }),
  );

  // Global API prefix
  app.setGlobalPrefix('api/v1');

  const port = process.env['PORT'] ?? 3001;
  await app.listen(port);
  // Internal port only: the public entry point is Nginx over HTTPS
  Logger.log(
    `SENTINEL backend listening on internal port ${port}`,
    'Bootstrap',
  );
}

void bootstrap();
