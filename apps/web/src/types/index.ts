// Auth types
export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  tenant_id: string;
  roles: string[];
}

export interface AuthContext {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
}

// Property types
export interface Property {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  property_type: string;
  unit_count: number;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface PropertyCreateRequest {
  name: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  property_type: string;
  unit_count: number;
}

export interface PropertyUpdateRequest extends Partial<PropertyCreateRequest> {}

// Invoice types
export interface Invoice {
  id: string;
  property_id: string;
  customer_id: string;
  amount: number;
  status: 'draft' | 'issued' | 'paid' | 'cancelled';
  invoice_date: string;
  due_date: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

// Payment types
export interface Payment {
  id: string;
  invoice_id: string;
  amount: number;
  payment_date: string;
  payment_method: string;
  status: 'pending' | 'completed' | 'failed';
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

// Audit trail
export interface AuditEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  changes: Record<string, unknown>;
  changed_by: string;
  changed_at: string;
  tenant_id: string;
}

// API error response
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
