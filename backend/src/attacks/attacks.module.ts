import { Module } from '@nestjs/common';
import { AttacksController } from './attacks.controller';
import { AttacksService } from './attacks.service';

@Module({
  controllers: [AttacksController],
  providers: [AttacksService]
})
export class AttacksModule {}
