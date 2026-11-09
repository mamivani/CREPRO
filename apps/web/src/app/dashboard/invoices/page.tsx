'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/services/api';
import { Invoice } from '@/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadInvoices();
  }, []);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getInvoices();
      setInvoices(response.data);
    } catch (error) {
      console.error('Failed to load invoices:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'bg-green-100 text-green-800';
      case 'issued':
        return 'bg-blue-100 text-blue-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6" data-testid="invoices-page">
      <div>
        <h2 className="text-3xl font-bold">Invoices</h2>
        <p className="text-muted-foreground">Manage your invoices and payments</p>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Loading invoices...</p>
        </div>
      ) : invoices.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No invoices found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {invoices.map((invoice) => (
            <Card key={invoice.id} data-testid={`invoice-card-${invoice.id}`}>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-semibold">Invoice #{invoice.id}</h3>
                    <p className="text-sm text-muted-foreground">
                      Customer ID: {invoice.customer_id}
                    </p>
                    <div className="mt-2 flex gap-4 text-sm">
                      <span>Amount: ${invoice.amount.toFixed(2)}</span>
                      <span>Due: {new Date(invoice.due_date).toLocaleDateString()}</span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                          invoice.status
                        )}`}
                        data-testid={`invoice-status-${invoice.id}`}
                      >
                        {invoice.status}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      data-testid={`view-invoice-button-${invoice.id}`}
                    >
                      View
                    </Button>
                    {invoice.status !== 'paid' && (
                      <Button size="sm" data-testid={`pay-invoice-button-${invoice.id}`}>
                        Pay
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
