import { WebSocketGateway } from '@nestjs/websockets';

// Not registered in WebsocketModule on purpose: an unregistered provider is
// never instantiated, so no Socket.io server is opened. It will be added to
// the module's providers once the handshake authenticates the JWT cookie.
@WebSocketGateway()
export class WebsocketGateway {}
