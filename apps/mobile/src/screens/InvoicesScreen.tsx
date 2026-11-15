import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, FlatList, ActivityIndicator, Alert, RefreshControl } from 'react-native';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { mobileApiClient } from '@/services/api';
import { Invoice } from '@/types';

export default function InvoicesScreen() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      const response = await mobileApiClient.getInvoices();
      setInvoices(response.data);
    } catch (error) {
      Alert.alert('Error', mobileApiClient.getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadInvoices();
    setRefreshing(false);
  };

  useEffect(() => {
    loadInvoices();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return '#059669';
      case 'sent':
        return '#2563EB';
      case 'overdue':
        return '#DC2626';
      case 'draft':
        return '#6B7280';
      default:
        return '#9CA3AF';
    }
  };

  const renderInvoice = ({ item }: { item: Invoice }) => (
    <Card>
      <View style={styles.invoiceHeader}>
        <View>
          <Text style={styles.invoiceNumber}>Invoice #{item.invoice_number}</Text>
          <Text style={styles.invoiceDate}>
            Due: {new Date(item.due_date).toLocaleDateString()}
          </Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
          <Text style={styles.statusText}>{item.status.toUpperCase()}</Text>
        </View>
      </View>

      <Text style={styles.amount}>${item.amount.toLocaleString()}</Text>
      
      {item.description && (
        <Text style={styles.description}>{item.description}</Text>
      )}

      <View style={styles.buttonGroup}>
        <Button
          title="View Details"
          onPress={() => {
            // Navigate to invoice details
          }}
          variant="primary"
        />
        {item.status !== 'paid' && (
          <Button
            title="Pay Now"
            onPress={() => {
              // Navigate to payment screen
            }}
            variant="secondary"
          />
        )}
      </View>
    </Card>
  );

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#208AEF" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={invoices}
        renderItem={renderInvoice}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No invoices found</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
  },
  listContent: {
    padding: 12,
  },
  invoiceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  invoiceNumber: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
  invoiceDate: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 4,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '600',
  },
  amount: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#208AEF',
    marginVertical: 8,
  },
  description: {
    fontSize: 13,
    color: '#6B7280',
    marginVertical: 8,
  },
  buttonGroup: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    color: '#6B7280',
  },
});
