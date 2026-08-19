import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { AttacksModule } from './attacks/attacks.module';
import { WebsocketModule } from './websocket/websocket.module';
import { ElasticsearchModule } from './elasticsearch/elasticsearch.module';

@Module({
  imports: [AuthModule, UsersModule, AttacksModule, WebsocketModule, ElasticsearchModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
