/**
 * shared/types/attack.types.ts
 *
 * Single source of truth for all attack-related data structures.
 * Every team member (frontend, backend, data) must import from here.
 * If you need to add or change a field, update this file and open a PR.
 */

// ─── Protocol types supported by our honeypots ───────────────────────────────

export type Protocol = 'ssh' | 'telnet' | 'smb' | 'ftp' | 'http' | 'other';

export type HoneypotType = 'cowrie' | 'dionaea' | 'heralding';

export type Severity = 'critical' | 'high' | 'medium' | 'low';

export type AttackType =
  | 'brute_force'
  | 'malware_drop'
  | 'port_scan'
  | 'exploit'
  | 'command_injection'
  | 'other';

export type UserRole = 'admin' | 'analyst' | 'viewer';

// ─── Core attack event (emitted via WebSocket and returned by the API) ────────

export interface AttackEvent {
  id: string;               // Elasticsearch document ID
  timestamp: string;        // ISO 8601: "2026-08-11T18:00:00.000Z"

  // Geographic origin
  source_ip: string;        // "185.234.12.5"
  source_country: string;   // ISO 3166-1 alpha-2: "RU", "CN", "US"
  source_city: string;      // "Moscow"
  source_lat: number;       // 55.7558
  source_lng: number;       // 37.6173

  // Attack classification
  protocol: Protocol;
  honeypot_type: HoneypotType;
  attack_type: AttackType;
  severity: Severity;

  // MITRE ATT&CK mapping
  mitre_tactic: string;     // "TA0006 - Credential Access"
  mitre_technique: string;  // "T1110 - Brute Force"

  // Threat intelligence
  virustotal: {
    malicious: number;      // number of engines flagging as malicious
    suspicious: number;
    harmless: number;
    score: number;          // 0-100, higher = more dangerous
  };

  // Cowrie-specific (SSH/Telnet honeypot)
  credentials_used?: {
    username: string;       // "root", "admin"
    password: string;       // "123456", "password"
  };
  session_commands?: string[];  // commands run by attacker in the shell

  // Dionaea-specific (malware honeypot)
  malware_hash?: string;    // SHA-256 of captured malware sample
}

// ─── WebSocket events emitted by the backend ─────────────────────────────────

export type WebSocketEventType =
  | 'new-attack'
  | 'honeypot-status'
  | 'notification'
  | 'user-online'
  | 'user-offline';

export interface WebSocketEvent {
  event: WebSocketEventType;
  data: AttackEvent | HoneypotStatus | NotificationPayload | UserStatusPayload;
}

// ─── Honeypot status (used by GET /api/v1/honeypots/status) ──────────────────

export interface HoneypotStatus {
  name: HoneypotType;
  status: 'running' | 'stopped' | 'error';
  attacks_last_hour: number;
  last_attack_at: string | null;   // ISO 8601 or null if no attacks yet
}

// ─── Notification payload ─────────────────────────────────────────────────────

export type NotificationType = 'attack_alert' | 'friend_request' | 'system';

export interface NotificationPayload {
  id: string;
  type: NotificationType;
  content: string;
  is_read: boolean;
  created_at: string;     // ISO 8601
  metadata?: Record<string, unknown>;
}

// ─── User online/offline status ───────────────────────────────────────────────

export interface UserStatusPayload {
  user_id: string;
  username: string;
  is_online: boolean;
  last_seen_at: string;   // ISO 8601
}

// ─── API response wrappers ────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}

export interface AttackStats {
  total_attacks: number;
  attacks_last_24h: number;
  top_countries: Array<{ country: string; count: number }>;
  top_protocols: Array<{ protocol: Protocol; count: number }>;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}
