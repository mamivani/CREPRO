export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'property_manager' | 'tenant';
}

export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Property {
  id: string;
  address: string;
  city: string;
  state: string;
  zipcode: string;
  country: string;
  property_type: string;
  bedrooms: number;
  bathrooms: number;
  square_feet: number;
  year_built: number;
  description?: string;
  rental_rate?: number;
  lease_start?: string;
  lease_end?: string;
  tenant_name?: string;
  tenant_contact?: string;
  created_at: string;
  updated_at: string;
}

export interface Invoice {
  id: string;
  property_id: string;
  invoice_number: string;
  due_date: string;
  amount: number;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  invoice_id: string;
  amount: number;
  payment_date: string;
  payment_method: string;
  reference?: string;
  created_at: string;
}

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
}

export interface CreatePropertyInput {
  address: string;
  city: string;
  state: string;
  zipcode: string;
  country: string;
  property_type: string;
  bedrooms: number;
  bathrooms: number;
  square_feet: number;
  year_built: number;
  description?: string;
  rental_rate?: number;
  lease_start?: string;
  lease_end?: string;
  tenant_name?: string;
  tenant_contact?: string;
}

export interface CreateInvoiceInput {
  property_id: string;
  invoice_number: string;
  due_date: string;
  amount: number;
  status?: string;
  description?: string;
}

export interface CreatePaymentInput {
  amount: number;
  payment_date: string;
  payment_method: string;
  reference?: string;
}
