import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import {
  appConfig,
  databaseConfig,
  elasticsearchConfig,
  jwtConfig,
} from './config/configuration';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { AttacksModule } from './attacks/attacks.module';
import { WebsocketModule } from './websocket/websocket.module';
import { ElasticsearchModule } from './elasticsearch/elasticsearch.module';
import { configSchema } from './config/config.schema';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '../.env',
      load: [appConfig, databaseConfig, jwtConfig, elasticsearchConfig],
      validationSchema: configSchema,
    }),
    AuthModule,
    UsersModule,
    AttacksModule,
    WebsocketModule,
    ElasticsearchModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
