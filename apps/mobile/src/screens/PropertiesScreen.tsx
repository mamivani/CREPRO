import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, FlatList, ActivityIndicator, Alert, RefreshControl } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { mobileApiClient } from '@/services/api';
import { Property } from '@/types';

export default function PropertiesScreen() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadProperties = async () => {
    try {
      setLoading(true);
      const response = await mobileApiClient.getProperties(0, 20);
      setProperties(response.data);
    } catch (error) {
      Alert.alert('Error', mobileApiClient.getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadProperties();
    setRefreshing(false);
  };

  useFocusEffect(
    React.useCallback(() => {
      loadProperties();
    }, [])
  );

  const renderProperty = ({ item }: { item: Property }) => (
    <Card>
      <Text style={styles.propertyTitle}>{item.address}</Text>
      <Text style={styles.propertySubtitle}>
        {item.city}, {item.state} {item.zipcode}
      </Text>
      <View style={styles.propertyDetails}>
        <View style={styles.detail}>
          <Text style={styles.detailLabel}>Type</Text>
          <Text style={styles.detailValue}>{item.property_type}</Text>
        </View>
        <View style={styles.detail}>
          <Text style={styles.detailLabel}>Bedrooms</Text>
          <Text style={styles.detailValue}>{item.bedrooms}</Text>
        </View>
        <View style={styles.detail}>
          <Text style={styles.detailLabel}>Bathrooms</Text>
          <Text style={styles.detailValue}>{item.bathrooms}</Text>
        </View>
      </View>
      {item.rental_rate && (
        <Text style={styles.rental}>
          Rental Rate: ${item.rental_rate.toLocaleString()}/month
        </Text>
      )}
      {item.tenant_name && (
        <Text style={styles.tenant}>Tenant: {item.tenant_name}</Text>
      )}
      <Button
        title="View Details"
        onPress={() => {
          // Navigate to property details
        }}
        variant="primary"
      />
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
        data={properties}
        renderItem={renderProperty}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No properties found</Text>
            <Button
              title="Add Property"
              onPress={() => {
                // Navigate to create property
              }}
              variant="primary"
            />
          </View>
        }
      />
      <View style={styles.fab}>
        <Button
          title="+ Add Property"
          onPress={() => {
            // Navigate to create property
          }}
          variant="primary"
        />
      </View>
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
    paddingBottom: 80,
  },
  propertyTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  propertySubtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 12,
  },
  propertyDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 12,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#E5E7EB',
  },
  detail: {
    alignItems: 'center',
  },
  detailLabel: {
    fontSize: 12,
    color: '#9CA3AF',
    marginBottom: 4,
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
  },
  rental: {
    fontSize: 14,
    color: '#059669',
    fontWeight: '500',
    marginVertical: 8,
  },
  tenant: {
    fontSize: 13,
    color: '#6B7280',
    marginBottom: 12,
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
    marginBottom: 16,
  },
  fab: {
    position: 'absolute',
    bottom: 20,
    right: 20,
    left: 20,
  },
});
